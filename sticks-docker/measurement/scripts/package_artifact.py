#!/usr/bin/env python3
"""
Create a self-contained reproducibility artifact for the procedural study.

The staged artifact preserves the frozen Docker-backed execution boundary while
excluding workspace residue, historical result archives, and reviewer-irrelevant
administrative material.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MEASUREMENT_ROOT = SCRIPT_DIR.parent
STICKS_DOCKER_ROOT = MEASUREMENT_ROOT.parent
REPO_ROOT = STICKS_DOCKER_ROOT.parent
DEFAULT_DEST = REPO_ROOT / "artifacts" / "sticks-review-artifact"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dest: Path) -> None:
    ensure_parent(dest)
    shutil.copy2(src, dest)


def copy_text_with_repo_relativization(src: Path, dest: Path) -> None:
    ensure_parent(dest)
    text = src.read_text(encoding="utf-8")
    repo_prefix = str(REPO_ROOT) + "/"
    text = text.replace(repo_prefix, "")
    dest.write_text(text, encoding="utf-8")


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            ".pytest_cache",
            "*.pyc",
            ".DS_Store",
        ),
    )


def remove_if_exists(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def empty_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def stage_shared_bundle(dest_root: Path) -> None:
    bundle_candidates = (
        REPO_ROOT / "sticks" / "data" / "stix" / "enterprise-attack.json",
        STICKS_DOCKER_ROOT / "sticks" / "data" / "stix" / "enterprise-attack.json",
    )
    for bundle_path in bundle_candidates:
        if bundle_path.is_file():
            copy_file(bundle_path, dest_root / "sticks" / "data" / "stix" / "enterprise-attack.json")
            break
    else:
        raise FileNotFoundError("Could not find frozen Enterprise ATT&CK bundle")

    license_candidates = (
        REPO_ROOT / "sticks" / "LICENSE",
        REPO_ROOT / "sticks" / "LICENSE.txt",
        STICKS_DOCKER_ROOT / "LICENSE",
        STICKS_DOCKER_ROOT / "LICENSE.txt",
    )
    for license_path in license_candidates:
        if license_path.is_file():
            copy_file(license_path, dest_root / "LICENSE.txt")
            break


def stage_measurement_boundary(dest_root: Path) -> None:
    measurement_dest = dest_root / "sticks-docker" / "measurement"
    for relative in [
        "README.md",
        "requirements.txt",
        "release_check.sh",
        "run_full_docker_audit.sh",
    ]:
        copy_file(MEASUREMENT_ROOT / relative, measurement_dest / relative)

    copy_file(
        MEASUREMENT_ROOT / "runtime" / "README.md",
        measurement_dest / "runtime" / "README.md",
    )

    copy_tree(MEASUREMENT_ROOT / "scripts", measurement_dest / "scripts")
    copy_tree(MEASUREMENT_ROOT / "tests", measurement_dest / "tests")

    result_files = [
        "README.md",
        "study_values_provenance.json",
        "STUDY_VALUES_PROVENANCE.md",
        "study_identifiability_provenance.json",
        "STUDY_IDENTIFIABILITY_PROVENANCE.md",
        "study_robustness_provenance.json",
        "STUDY_ROBUSTNESS_PROVENANCE.md",
        "supplementary_provenance.json",
        "SUPPLEMENTARY_PROVENANCE.md",
        "docker_runtime_context_latest.json",
        "DOCKER_RUNTIME_CONTEXT_LATEST.md",
        "docker_caldera_execution_latest.json",
        "DOCKER_CALDERA_EXECUTION_LATEST.md",
        "docker_execution_findings_latest.json",
        "DOCKER_EXECUTION_FINDINGS_LATEST.md",
    ]
    for relative in result_files:
        copy_text_with_repo_relativization(
            MEASUREMENT_ROOT / "results" / relative,
            measurement_dest / "results" / relative,
        )


def stage_frozen_artifact(dest_root: Path) -> None:
    sticks_dest = dest_root / "sticks-docker" / "sticks"
    copy_tree(STICKS_DOCKER_ROOT / "sticks" / "data" / "api", sticks_dest / "data" / "api")

    docker_dest = dest_root / "sticks-docker" / "docker"
    copy_file(STICKS_DOCKER_ROOT / "docker" / "docker-compose.yml", docker_dest / "docker-compose.yml")
    copy_file(STICKS_DOCKER_ROOT / "architecture.png", dest_root / "sticks-docker" / "architecture.png")
    copy_tree(STICKS_DOCKER_ROOT / "docker" / ".docker" / "caldera", docker_dest / ".docker" / "caldera")
    copy_tree(STICKS_DOCKER_ROOT / "docker" / ".docker" / "nginx", docker_dest / ".docker" / "nginx")
    copy_tree(STICKS_DOCKER_ROOT / "docker" / ".docker" / "kali", docker_dest / ".docker" / "kali")
    copy_tree(STICKS_DOCKER_ROOT / "docker" / ".docker" / "db", docker_dest / ".docker" / "db")

    remove_if_exists(docker_dest / ".docker" / "caldera" / "plugins" / "ssl")
    remove_if_exists(docker_dest / ".docker" / "caldera" / "plugins" / "debrief" / "docs")

    empty_directory(docker_dest / ".docker" / "db" / "dbdata")
    empty_directory(docker_dest / "kali-data")
    remove_if_exists(docker_dest / ".docker" / "nginx" / "var" / "www" / "html" / "tmp")
    write_text(
        docker_dest / ".docker" / "nginx" / "var" / "www" / "html" / "tmp" / ".gitkeep",
        "",
    )

    write_text(
        sticks_dest / "README.md",
        "\n".join(
            [
                "# Frozen STICKS Layer",
                "",
                "This subtree contains the curated Caldera API payloads consumed by",
                "the measurement boundary. It is intentionally minimal and should be",
                "treated as read-only during artifact validation.",
                "",
                "The primary entry points are the repository-root",
                "`run_review_check.sh` wrapper and the canonical verifier at",
                "`sticks-docker/measurement/release_check.sh`.",
                "",
            ]
        ),
    )

    write_text(
        docker_dest / "README.md",
        "\n".join(
            [
                "# Frozen Docker Substrate",
                "",
                "This directory contains the frozen shared-substrate Docker context used",
                "by the execution audit.",
                "",
                "Validation paths:",
                "",
                "- Fast validation: do not enter this directory directly; run",
                "  `bash run_review_check.sh` from the repository root.",
                "- Full Docker replay: run",
                "  `bash sticks-docker/measurement/run_full_docker_audit.sh` from the",
                "  repository root if you want to rebuild the shared substrate and rerun",
                "  the eight curated adversaries end to end.",
                "",
                "The staged artifact intentionally excludes runtime residue such as",
                "persistent Kali history and populated database state.",
                "",
            ]
        ),
    )


def write_artifact_docs(dest_root: Path) -> None:
    write_text(
        dest_root / "run_review_check.sh",
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
                'cd "$ROOT_DIR/sticks-docker/measurement"',
                "bash release_check.sh",
                "",
            ]
        ),
    )
    (dest_root / "run_review_check.sh").chmod(0o755)
    (dest_root / "sticks-docker" / "measurement" / "release_check.sh").chmod(0o755)
    (dest_root / "sticks-docker" / "measurement" / "run_full_docker_audit.sh").chmod(0o755)

    write_text(
        dest_root / ".gitattributes",
        "\n".join(
            [
                "* text=auto eol=lf",
                "*.sh text eol=lf",
                "*.py text eol=lf",
                "*.yml text eol=lf",
                "*.yaml text eol=lf",
                "",
            ]
        ),
    )

    write_text(
        dest_root / ".gitignore",
        "\n".join(
            [
                ".DS_Store",
                "__pycache__/",
                "*.pyc",
                "sticks-docker/measurement/runtime/docker-context/",
                "sticks-docker/measurement/runtime/curated-api/",
                "",
            ]
        ),
    )

    write_text(
        dest_root / "README.md",
        "\n".join(
            [
                "# Procedural Reproducibility Artifact",
                "",
                "This repository contains the reproducibility surface for the",
                "procedural-semantics study in structured CTI.",
                "",
                "## Entry points",
                "",
                "Fast validation path:",
                "",
                "```bash",
                "bash run_review_check.sh",
                "```",
                "",
                "This reruns the structural measurement scripts, refreshes the frozen",
                "Docker audit summaries, and executes the measurement unit tests.",
                "",
                "Optional full Docker replay:",
                "",
                "```bash",
                "bash sticks-docker/measurement/run_full_docker_audit.sh",
                "```",
                "",
                "This heavier path prepares a disposable Docker runtime context, brings",
                "up the shared-substrate lab, reruns the eight curated adversaries, and",
                "regenerates the execution summaries used by the study.",
                "",
                "## What this artifact supports directly",
                "",
                "- Self-containment: the repository includes the files and `LICENSE` needed for validation.",
                "- Exercisability: `bash run_review_check.sh` recomputes the released measurement",
                "  outputs and validates the frozen execution summaries.",
                "- Main-result reproduction: the optional Docker path rebuilds the shared lab and",
                "  reruns the eight curated adversaries end to end from the published artifact.",
                "",
                "## Runtime expectations",
                "",
                "- Python 3.11+",
                "- `docker-compose` available on `PATH` only for the optional full replay",
                "- Fast validation runtime: about 3 to 4 minutes on a laptop-class machine",
                "- Full Docker replay runtime: substantially longer and dependent on Docker build cache",
                "- No external API keys are required for the validation paths",
                "- Default Caldera and database credentials in the Docker context are disposable",
                "  local-lab constants; they are not external service credentials.",
                "- Code-signing key material used by the optional Docker replay is generated",
                "  inside the disposable lab at startup rather than stored in the repository.",
                "- For Docker Desktop on macOS, run the full Docker replay from a regular local clone",
                "  path (for example under your home directory) rather than a transient temp directory,",
                "  so the Caldera bind mount remains visible to the containers.",
                "",
                "## Repository layout",
                "",
                "- `run_review_check.sh`: root-level validation wrapper.",
                "- `sticks/`: shared ATT&CK v18.1 bundle required by the verifier.",
                "- `sticks-docker/measurement/`: measurement scripts, tests, verifier, and latest audit outputs.",
                "- `sticks-docker/sticks/`: curated Caldera API payloads used by the Docker replay.",
                "- `sticks-docker/docker/`: frozen shared-substrate Docker context with runtime residue removed.",
                "",
                "## Reproduction contract",
                "",
                "If `bash run_review_check.sh` passes from the repository root, the",
                "artifact has enough material to rerun the procedural measurements and",
                "refresh the frozen Docker audit summaries.",
                "",
                "The optional Docker replay remains explicitly labeled as a shared-substrate",
                "execution audit, not isolated per-campaign historical replay.",
                "",
            ]
        ),
    )

    write_text(
        dest_root / "ARTIFACT_MANIFEST.md",
        "\n".join(
            [
                "# Artifact Manifest",
                "",
                "## Included components",
                "",
                "- `run_review_check.sh`: root-level fast validation entry point.",
                "- `sticks/data/stix/enterprise-attack.json`: the Enterprise ATT&CK v18.1 bundle used by the measurement scripts.",
                "- `sticks-docker/measurement/`: measurement scripts, tests, latest audit outputs, runtime docs, and the canonical verifier.",
                "- `sticks-docker/sticks/`: curated Caldera API payloads.",
                "- `sticks-docker/docker/`: frozen shared-substrate Docker context with runtime residue removed.",
                "",
                "## Excluded components",
                "",
                "- Historical result archives and timestamped rerun logs not required by the validation path.",
                "- Persistent Kali shell history and SSH known-hosts residue.",
                "- Populated MariaDB state from prior runs.",
                "- Unrelated workspace material from the broader development tree.",
                "",
                "## Reproduction modes",
                "",
                "- Fast mode (`run_review_check.sh`): recomputes the measurement outputs from the staged artifact plus the frozen latest Docker audit summaries.",
                "- Full Docker mode (`sticks-docker/measurement/run_full_docker_audit.sh`): rebuilds the shared-substrate lab and reruns the eight curated adversaries end to end.",
                "",
                "If this artifact is later mirrored to a tagged public repository or a DOI-backed",
                "archival snapshot, it should preserve the same contents and entry points.",
                "",
            ]
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help="Destination directory for the staged review artifact.",
    )
    args = parser.parse_args()

    dest_root = args.dest.resolve()
    if dest_root.exists():
        shutil.rmtree(dest_root)
    dest_root.mkdir(parents=True, exist_ok=True)

    stage_shared_bundle(dest_root)
    stage_measurement_boundary(dest_root)
    stage_frozen_artifact(dest_root)
    write_artifact_docs(dest_root)

    print(f"Staged procedural artifact at {dest_root}")


if __name__ == "__main__":
    main()
