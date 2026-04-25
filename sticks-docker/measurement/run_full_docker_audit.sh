#!/usr/bin/env bash
set -euo pipefail

MEASUREMENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${MEASUREMENT_DIR}/../.." && pwd)"
RUNTIME_CONTEXT="${MEASUREMENT_DIR}/runtime/docker-context"
API_OVERLAY="${MEASUREMENT_DIR}/runtime/curated-api"

cleanup() {
  if [[ -f "${RUNTIME_CONTEXT}/docker-compose.yml" ]]; then
    (
      cd "${RUNTIME_CONTEXT}"
      docker-compose down -v >/dev/null 2>&1 || true
    )
  fi
}

trap cleanup EXIT

cd "${ROOT_DIR}"

python3 sticks-docker/measurement/scripts/prepare_docker_runtime_context.py \
  --output-dir "${RUNTIME_CONTEXT}" \
  --api-overlay-dir "${API_OVERLAY}"

(
  cd "${RUNTIME_CONTEXT}"
  docker-compose up -d --build
)

python3 sticks-docker/measurement/scripts/run_curated_caldera_campaigns.py \
  --curated-api-dir "${API_OVERLAY}" \
  --agent-timeout 900 \
  --substrate-timeout 1800
python3 sticks-docker/measurement/scripts/summarize_docker_findings.py

echo "PASS: full STICKS Docker audit reran successfully"
