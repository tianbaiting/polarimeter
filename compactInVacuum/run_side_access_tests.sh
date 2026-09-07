#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/run_boxed_tests.sh"
micromamba run -n anaroot-env python -m pytest -q "${SCRIPT_DIR}/tests/test_side_access.py"
TEST_FILE="${SCRIPT_DIR}/tests/side_access_runtime.py"
freecadcmd -c "import runpy; m=runpy.run_path(r'${TEST_FILE}'); raise SystemExit(m['main']())"
