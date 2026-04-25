from __future__ import annotations

from functools import lru_cache
import importlib.util
import sys
from pathlib import Path


MEASUREMENT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = MEASUREMENT_ROOT / "scripts" / "analyze_identifiability.py"


@lru_cache(maxsize=1)
def _load_module():
    spec = importlib.util.spec_from_file_location("study_identifiability", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reduce_difference_sets_drops_duplicates_and_supersets() -> None:
    module = _load_module()

    reduced = module.reduce_difference_sets(
        (
            frozenset({"T1", "T2"}),
            frozenset({"T1"}),
            frozenset({"T1", "T2"}),
            frozenset({"T2", "T3"}),
        )
    )

    assert reduced == (frozenset({"T1"}), frozenset({"T2", "T3"}))


def test_find_minimum_witness_handles_size_two_case() -> None:
    module = _load_module()

    witness = module.find_minimum_witness(
        (
            frozenset({"T2"}),
            frozenset({"T3"}),
        )
    )

    assert witness == ("T2", "T3")


def test_find_minimum_witness_prefers_single_technique_when_available() -> None:
    module = _load_module()

    witness = module.find_minimum_witness(
        (
            frozenset({"T2"}),
            frozenset({"T2", "T3"}),
            frozenset({"T1", "T2"}),
        )
    )

    assert witness == ("T2",)


def test_summarize_profiles_marks_subsumed_profile_impossible() -> None:
    module = _load_module()

    by_id = {
        "attack-pattern--1": {
            "external_references": [{"source_name": "mitre-attack", "external_id": "T1"}],
            "name": "One",
        },
        "attack-pattern--2": {
            "external_references": [{"source_name": "mitre-attack", "external_id": "T2"}],
            "name": "Two",
        },
        "attack-pattern--3": {
            "external_references": [{"source_name": "mitre-attack", "external_id": "T3"}],
            "name": "Three",
        },
    }
    profiles = [
        {
            "id": "campaign--a",
            "name": "A",
            "technique_ids": frozenset({"attack-pattern--1", "attack-pattern--2"}),
        },
        {
            "id": "campaign--b",
            "name": "B",
            "technique_ids": frozenset(
                {"attack-pattern--1", "attack-pattern--2", "attack-pattern--3"}
            ),
        },
    ]

    summary = module.summarize_profiles("campaign", profiles, by_id)
    rows = {row["name"]: row for row in summary["rows"]}

    assert rows["A"]["min_witness_size"] is None
    assert rows["A"]["blocker_names"] == ["B"]
    assert rows["B"]["min_witness_size"] == 1
    assert rows["B"]["witness_technique_ids"] == ["T3"]
