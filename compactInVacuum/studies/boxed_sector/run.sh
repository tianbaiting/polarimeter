#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${SCRIPT_DIR}/state"
export CIV_MODULE_NAME=compactBoxedSectorStudy
exec flock --wait 60 "${SCRIPT_DIR}/state/state.lock" \
  "${SCRIPT_DIR}/../../run_compactInVacuum.sh" "$@" \
  --pipeline-index "${SCRIPT_DIR}/../../../codex_targets.yaml"
