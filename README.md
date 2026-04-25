# Procedural Reproducibility Artifact

This repository contains the reproducibility surface for the
procedural-semantics study in structured CTI.

## Entry points

Fast validation path:

```bash
bash run_review_check.sh
```

This reruns the structural measurement scripts, refreshes the frozen
Docker audit summaries, and executes the measurement unit tests.

Optional full Docker replay:

```bash
bash sticks-docker/measurement/run_full_docker_audit.sh
```

This heavier path prepares a disposable Docker runtime context, brings
up the shared-substrate lab, reruns the eight curated adversaries, and
regenerates the execution summaries used by the study.

## What this artifact supports directly

- Self-containment: the repository includes the files and `LICENSE` needed for validation.
- Exercisability: `bash run_review_check.sh` recomputes the released measurement
  outputs and validates the frozen execution summaries.
- Main-result reproduction: the optional Docker path rebuilds the shared lab and
  reruns the eight curated adversaries end to end from the published artifact.

## Runtime expectations

- Python 3.11+
- `docker-compose` available on `PATH` only for the optional full replay
- Fast validation runtime: about 3 to 4 minutes on a laptop-class machine
- Full Docker replay runtime: substantially longer and dependent on Docker build cache
- No external API keys are required for the validation paths
- Default Caldera and database credentials in the Docker context are disposable
  local-lab constants; they are not external service credentials.
- Code-signing key material used by the optional Docker replay is generated
  inside the disposable lab at startup rather than stored in the repository.
- For Docker Desktop on macOS, run the full Docker replay from a regular local clone
  path (for example under your home directory) rather than a transient temp directory,
  so the Caldera bind mount remains visible to the containers.

## Repository layout

- `run_review_check.sh`: root-level validation wrapper.
- `sticks/`: shared ATT&CK v18.1 bundle required by the verifier.
- `sticks-docker/measurement/`: measurement scripts, tests, verifier, and latest audit outputs.
- `sticks-docker/sticks/`: curated Caldera API payloads used by the Docker replay.
- `sticks-docker/docker/`: frozen shared-substrate Docker context with runtime residue removed.

## Reproduction contract

If `bash run_review_check.sh` passes from the repository root, the
artifact has enough material to rerun the procedural measurements and
refresh the frozen Docker audit summaries.

The optional Docker replay remains explicitly labeled as a shared-substrate
execution audit, not isolated per-campaign historical replay.
