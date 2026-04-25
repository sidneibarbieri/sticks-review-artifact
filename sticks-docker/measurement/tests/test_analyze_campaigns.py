from __future__ import annotations

from functools import lru_cache
import importlib.util
import sys
from pathlib import Path


MEASUREMENT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = MEASUREMENT_ROOT / "scripts" / "analyze_campaigns.py"


@lru_cache(maxsize=1)
def _load_module():
    spec = importlib.util.spec_from_file_location("study_docker_measurement", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def _load_report():
    module = _load_module()
    return module, module.compute_study_values(module.DEFAULT_BUNDLE)


def test_generated_macros_cover_expected_measurement_surface() -> None:
    module, report = _load_report()

    generated_macros = set(report["macro_values"])
    rendered_macros = {
        line.split("{\\", 1)[1].split("}", 1)[0]
        for line in module.render_macro_snapshot(report).splitlines()
        if line.startswith("\\newcommand{\\")
    }

    assert len(generated_macros) == 40
    assert generated_macros == rendered_macros


def test_platform_agnostic_classifier_matches_reported_macro_and_excludes_host_platforms() -> None:
    module, report = _load_report()

    classifier = report["provenance"]["platform_agnostic_classifier"]
    listed = classifier["techniques"]
    assert int(report["macro_values"]["nPlatformAgnosticTechniques"]) == len(listed)

    for item in listed:
        assert not (set(item["platforms"]) & module.CONCRETE_HOST_PLATFORMS)


def test_case_study_provenance_is_explicit_for_shadowray_and_soft_cell() -> None:
    _, report = _load_report()

    case_studies = {item["display_name"]: item for item in report["provenance"]["case_studies"]}

    assert set(case_studies) == {"ShadowRay", "Soft Cell"}
    assert case_studies["ShadowRay"]["local_campaign_id"] == "0.shadowray"
    assert case_studies["Soft Cell"]["stix_name"] == "GALLIUM"
    assert case_studies["Soft Cell"]["description_mentions_display_name"] is True
