# Artifact Manifest

## Included components

- `run_review_check.sh`: root-level fast validation entry point.
- `sticks/data/stix/enterprise-attack.json`: the Enterprise ATT&CK v18.1 bundle used by the measurement scripts.
- `sticks-docker/measurement/`: measurement scripts, tests, latest audit outputs, runtime docs, and the canonical verifier.
- `sticks-docker/sticks/`: curated Caldera API payloads.
- `sticks-docker/docker/`: frozen shared-substrate Docker context with runtime residue removed.

## Excluded components

- Historical result archives and timestamped rerun logs not required by the validation path.
- Persistent Kali shell history and SSH known-hosts residue.
- Populated MariaDB state from prior runs.
- Unrelated workspace material from the broader development tree.

## Reproduction modes

- Fast mode (`run_review_check.sh`): recomputes the measurement outputs from the staged artifact plus the frozen latest Docker audit summaries.
- Full Docker mode (`sticks-docker/measurement/run_full_docker_audit.sh`): rebuilds the shared-substrate lab and reruns the eight curated adversaries end to end.

If this artifact is later mirrored to a tagged public repository or a DOI-backed
archival snapshot, it should preserve the same contents and entry points.
