# Procedural Measurement Scripts

Each script in this directory has a narrow purpose and writes explicit output
files under `sticks-docker/measurement/results/`.

Rules:

- Inputs come from the frozen artifact tree or files copied into this
  measurement boundary.
- Scripts do not depend on private writing paths.
- Docker replay orchestration talks to Caldera through its API rather than
  through legacy helper code.
- Comments stay short and operational.

Main entry points:

- `analyze_campaigns.py`: corpus coverage, clustering, and case-study values.
- `analyze_identifiability.py`: positive-evidence profile identifiability.
- `analyze_robustness.py`: clustering and overlap sensitivity checks.
- `analyze_supplementary.py`: field-population, itemset, and Docker breakdown
  provenance.
- `prepare_docker_runtime_context.py`: disposable full-replay context setup.
- `run_curated_caldera_campaigns.py`: full replay orchestration for curated
  adversaries.
- `summarize_docker_findings.py`: consolidated Docker execution findings.
