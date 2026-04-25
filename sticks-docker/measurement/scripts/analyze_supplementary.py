#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path


MEASUREMENT_ROOT = Path(__file__).resolve().parent.parent
STICKS_DOCKER_ROOT = MEASUREMENT_ROOT.parent
WORKSPACE_ROOT = STICKS_DOCKER_ROOT.parent


def resolve_enterprise_bundle() -> Path:
    candidates = (
        WORKSPACE_ROOT / "sticks" / "data" / "stix" / "enterprise-attack.json",
        STICKS_DOCKER_ROOT / "sticks" / "data" / "stix" / "enterprise-attack.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


ENTERPRISE_BUNDLE = resolve_enterprise_bundle()
DOCKER_EXECUTION = MEASUREMENT_ROOT / "results" / "docker_caldera_execution_latest.json"
DOCKER_FINDINGS = MEASUREMENT_ROOT / "results" / "docker_execution_findings_latest.json"
PROVENANCE_MD = MEASUREMENT_ROOT / "results" / "SUPPLEMENTARY_PROVENANCE.md"
PROVENANCE_JSON = MEASUREMENT_ROOT / "results" / "supplementary_provenance.json"


def display_path(path: Path) -> str:
    for root in (WORKSPACE_ROOT, MEASUREMENT_ROOT):
        if path.is_relative_to(root):
            return path.relative_to(root).as_posix()
    return path.as_posix()


def load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def active_attack_patterns(bundle: dict) -> list[dict]:
    out = []
    for obj in bundle["objects"]:
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        ext_ids = [
            ref.get("external_id", "")
            for ref in obj.get("external_references", [])
            if ref.get("source_name") == "mitre-attack"
        ]
        if any(ext.startswith("T") for ext in ext_ids):
            out.append(obj)
    return out


def nonempty(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(nonempty(v) for v in value)
    return True


def field_population(attack_patterns: list[dict]) -> dict[str, dict[str, int]]:
    fields = [
        "kill_chain_phases",
        "x_mitre_platforms",
        "x_mitre_system_requirements",
        "x_mitre_detection",
        "x_mitre_data_sources",
        "x_mitre_permissions_required",
    ]
    stats = {}
    for field in fields:
        present = sum(1 for obj in attack_patterns if field in obj)
        non_empty = sum(1 for obj in attack_patterns if nonempty(obj.get(field)))
        stats[field] = {"present": present, "non_empty": non_empty}
    return stats


def campaign_sets(bundle: dict) -> list[list[str]]:
    tech_ids = {}
    for obj in active_attack_patterns(bundle):
        ext_id = next(
            ref["external_id"]
            for ref in obj.get("external_references", [])
            if ref.get("source_name") == "mitre-attack" and ref.get("external_id", "").startswith("T")
        )
        tech_ids[obj["id"]] = ext_id

    campaigns = {
        obj["id"]: obj.get("name")
        for obj in bundle["objects"]
        if obj.get("type") == "campaign"
        and not obj.get("revoked")
        and not obj.get("x_mitre_deprecated")
    }
    rels = [
        obj
        for obj in bundle["objects"]
        if obj.get("type") == "relationship"
        and obj.get("relationship_type") == "uses"
        and not obj.get("revoked")
        and not obj.get("x_mitre_deprecated")
    ]

    campaign_techniques: list[list[str]] = []
    for campaign_id in campaigns:
        techniques = sorted(
            {
                tech_ids[rel["target_ref"]]
                for rel in rels
                if rel.get("source_ref") == campaign_id and rel.get("target_ref") in tech_ids
            }
        )
        if techniques:
            campaign_techniques.append(techniques)
    return campaign_techniques


def itemset_support(campaigns: list[list[str]], max_size: int = 5) -> list[dict[str, float | int]]:
    out = []
    total = len(campaigns)
    for size in range(1, max_size + 1):
        counter = Counter()
        for techniques in campaigns:
            if len(techniques) >= size:
                counter.update(itertools.combinations(techniques, size))
        top_itemset, top_support = counter.most_common(1)[0]
        out.append(
            {
                "size": size,
                "max_support": top_support,
                "fraction_pct": round(100.0 * top_support / total, 1),
                "itemset": list(top_itemset),
            }
        )
    return out


def docker_breakdown() -> list[dict]:
    execution = load_json(DOCKER_EXECUTION)
    findings = load_json(DOCKER_FINDINGS)
    by_operation = {op["name"]: op for op in execution["operations"]}
    rows = []
    for op in findings["execution"]["per_operation"]:
        exec_op = by_operation[op["name"]]
        rows.append(
            {
                "operation": op["name"],
                "adversary": op["adversary_name"],
                "successful_links": op["successful_links"],
                "failed_links": op["failed_links"],
                "pending_links": op["pending_links"],
                "chain_count": op["chain_count"],
                "end_marker": exec_op.get("last_link", {}).get("name", "").startswith("END OF"),
                "residual_nonzero": len(op["nonzero_links"]),
            }
        )
    return rows


def write_provenance(field_stats: dict, itemsets: list[dict], docker_rows: list[dict], total_attack_patterns: int) -> None:
    payload = {
        "bundle": display_path(ENTERPRISE_BUNDLE),
        "docker_execution": display_path(DOCKER_EXECUTION),
        "docker_findings": display_path(DOCKER_FINDINGS),
        "active_attack_patterns": total_attack_patterns,
        "field_population": field_stats,
        "itemset_support": itemsets,
        "docker_breakdown": docker_rows,
    }
    PROVENANCE_JSON.write_text(json.dumps(payload, indent=2))

    lines = [
        "# Supplementary Measurement Provenance",
        "",
        f"- Bundle: `{display_path(ENTERPRISE_BUNDLE)}`",
        f"- Docker execution report: `{display_path(DOCKER_EXECUTION)}`",
        f"- Docker findings report: `{display_path(DOCKER_FINDINGS)}`",
        f"- Active Enterprise attack-patterns: `{total_attack_patterns}`",
        "",
        "## Automation-Relevant Field Population",
        "",
    ]
    for field, stats in field_stats.items():
        lines.append(f"- `{field}`: present `{stats['present']}`, non-empty `{stats['non_empty']}`")
    lines.extend(
        [
            "",
            "## Non-Sequential Campaign Itemset Support",
            "",
        ]
    )
    for row in itemsets:
        lines.append(
            f"- Size `{row['size']}`: max support `{row['max_support']}` "
            f"({row['fraction_pct']:.1f}%), example `{', '.join(row['itemset'])}`"
        )
    lines.extend(
        [
            "",
            "## Docker Audit Breakdown",
            "",
        ]
    )
    for row in docker_rows:
        lines.append(
            f"- `{row['adversary']}`: successful links `{row['successful_links']}`, "
            f"end marker `{row['end_marker']}`, residual non-zero `{row['residual_nonzero']}`"
        )
    PROVENANCE_MD.write_text("\n".join(lines) + "\n")


def main() -> None:
    bundle = load_json(ENTERPRISE_BUNDLE)
    attack_patterns = active_attack_patterns(bundle)
    field_stats = field_population(attack_patterns)
    itemsets = itemset_support(campaign_sets(bundle))
    docker_rows = docker_breakdown()
    write_provenance(field_stats, itemsets, docker_rows, len(attack_patterns))
    print(f"Wrote {PROVENANCE_MD}")
    print(f"Wrote {PROVENANCE_JSON}")


if __name__ == "__main__":
    main()
