#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
micromamba run -n anaroot-env python -m pytest -q \
  "${MODULE_ROOT}/tests/test_boxed_config.py" \
  "${MODULE_ROOT}/tests/test_platform_config.py" \
  "${MODULE_ROOT}/tests/test_geometry.py"
freecadcmd -c "import runpy; m=runpy.run_path(r'${MODULE_ROOT}/tests/boxed_motion_runtime.py'); raise SystemExit(m['main']())"
