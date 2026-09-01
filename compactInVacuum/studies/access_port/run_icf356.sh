#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CIV_MODULE_NAME="compactOneAfterSRCICF356Study"
exec "${SCRIPT_DIR}/../../run_compactInVacuum.sh" "$@" \
  --pipeline-index "${SCRIPT_DIR}/codex_targets.yaml"
