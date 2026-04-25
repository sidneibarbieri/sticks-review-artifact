# Frozen Docker Substrate

This directory contains the frozen shared-substrate Docker context used
by the execution audit.

Validation paths:

- Fast validation: do not enter this directory directly; run
  `bash run_review_check.sh` from the repository root.
- Full Docker replay: run
  `bash sticks-docker/measurement/run_full_docker_audit.sh` from the
  repository root if you want to rebuild the shared substrate and rerun
  the eight curated adversaries end to end.

The staged artifact intentionally excludes runtime residue such as
persistent Kali history and populated database state.
