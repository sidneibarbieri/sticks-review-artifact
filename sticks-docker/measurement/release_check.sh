#!/usr/bin/env bash
set -euo pipefail

MEASUREMENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${MEASUREMENT_DIR}/../.." && pwd)"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sticks-release-check.XXXXXX")"
RUNTIME_CONTEXT="${TEMP_DIR}/docker-context"
API_OVERLAY="${TEMP_DIR}/curated-api"
export PYTHONDONTWRITEBYTECODE=1

resolve_python_bin() {
  local candidate
  for candidate in /opt/homebrew/bin/python3 python3 python3.14 python; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      if "${candidate}" -c 'import pytest, sys; print(sys.executable)' >/tmp/sticks-python-bin 2>/dev/null; then
        cat /tmp/sticks-python-bin
        rm -f /tmp/sticks-python-bin
        return 0
      fi
    fi
  done

  echo "release_check.sh could not find a Python interpreter with pytest installed" >&2
  return 1
}

PYTHON_BIN="$(resolve_python_bin)"

resolve_bundle_path() {
  local candidate
  for candidate in \
    "${ROOT_DIR}/sticks/data/stix/enterprise-attack.json" \
    "${ROOT_DIR}/sticks-docker/sticks/data/stix/enterprise-attack.json"
  do
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  echo "release_check.sh could not find the frozen Enterprise ATT&CK bundle" >&2
  echo "Expected one of:" >&2
  echo "  ${ROOT_DIR}/sticks/data/stix/enterprise-attack.json" >&2
  echo "  ${ROOT_DIR}/sticks-docker/sticks/data/stix/enterprise-attack.json" >&2
  return 1
}

BUNDLE_PATH="$(resolve_bundle_path)"

cleanup() {
  rm -rf "${TEMP_DIR}"
}

trap cleanup EXIT

cd "${ROOT_DIR}"

"${PYTHON_BIN}" sticks-docker/measurement/scripts/analyze_campaigns.py \
  --bundle "${BUNDLE_PATH}"
"${PYTHON_BIN}" sticks-docker/measurement/scripts/analyze_identifiability.py \
  --bundle "${BUNDLE_PATH}"
"${PYTHON_BIN}" sticks-docker/measurement/scripts/analyze_robustness.py
"${PYTHON_BIN}" sticks-docker/measurement/scripts/analyze_supplementary.py
"${PYTHON_BIN}" sticks-docker/measurement/scripts/prepare_docker_runtime_context.py \
  --output-dir "${RUNTIME_CONTEXT}" \
  --api-overlay-dir "${API_OVERLAY}"
"${PYTHON_BIN}" sticks-docker/measurement/scripts/summarize_docker_findings.py

(
  cd sticks-docker/measurement
  PYTHONDONTWRITEBYTECODE=1 "${PYTHON_BIN}" -m pytest -q -p no:cacheprovider
)

echo "PASS: procedural measurement + frozen docker audit are consistent"
