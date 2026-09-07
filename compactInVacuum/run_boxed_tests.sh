#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/studies/boxed_sector/run_tests.sh"
TEST_FILE="${SCRIPT_DIR}/tests/boxed_deployment_runtime.py"
freecadcmd -c "import runpy; scope=runpy.run_path(r'${TEST_FILE}'); raise SystemExit(scope['main']())"
