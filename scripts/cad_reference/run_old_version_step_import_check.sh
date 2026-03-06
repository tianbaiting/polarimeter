#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export OLD_VERSION_STEP_CHECK_ARGS_JSON="$(
  python3 - "$@" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1:]))
PY
)"

freecadcmd -c "import json, os, runpy, sys; from pathlib import Path; script = Path(r'${SCRIPT_DIR}/check_step_import_freecad.py').resolve(); sys.argv = [str(script)] + json.loads(os.environ['OLD_VERSION_STEP_CHECK_ARGS_JSON']); runpy.run_path(str(script), run_name='__main__')"
