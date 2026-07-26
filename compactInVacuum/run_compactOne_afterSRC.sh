#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CIV_MODULE_NAME="compactOneAfterSRC"
export CIV_DEFAULT_CONFIG_PATH="${SCRIPT_DIR}/config/afterSRC_compact.yaml"
exec "${SCRIPT_DIR}/run_compactInVacuum.sh" "$@"
