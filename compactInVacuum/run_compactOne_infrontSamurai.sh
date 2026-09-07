#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CIV_MODULE_NAME="compactOneInfrontSamurai"
export CIV_DEFAULT_CONFIG_PATH="${SCRIPT_DIR}/config/infrontSamurai_compact.yaml"
exec flock --wait 60 "${SCRIPT_DIR}/compactOne_infrontSamurai.state.lock" "${SCRIPT_DIR}/run_compactInVacuum.sh" "$@"
