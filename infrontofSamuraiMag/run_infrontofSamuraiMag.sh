#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export IFSM_ARGS_JSON="$(python3 - "$@" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1:]))
PY
)"

freecadcmd -c "import json, os, sys; from pathlib import Path; sys.path.insert(0, str(Path(r'${SCRIPT_DIR}/src').resolve())); from ifsm.cli import main; raise SystemExit(main(json.loads(os.environ['IFSM_ARGS_JSON'])))"
