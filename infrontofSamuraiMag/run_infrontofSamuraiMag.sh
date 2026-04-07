#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${TMPDIR:-/tmp}/infrontofSamuraiMag-freecad"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${RUNTIME_DIR}/xdg-cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${RUNTIME_DIR}/xdg-config}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export QT_OPENGL="${QT_OPENGL:-software}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export IFSM_MODULE_NAME="${IFSM_MODULE_NAME:-infrontofSamuraiMag}"
export IFSM_DEFAULT_CONFIG_PATH="${IFSM_DEFAULT_CONFIG_PATH:-${SCRIPT_DIR}/config/default_infront.yaml}"
mkdir -p "${XDG_CACHE_HOME}/FreeCAD" "${XDG_CONFIG_HOME}/FreeCAD"
export IFSM_ARGS_JSON="$(python3 - "$@" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1:]))
PY
)"

freecadcmd -c "import json, os, sys; from pathlib import Path; sys.path.insert(0, str(Path(r'${SCRIPT_DIR}/src').resolve())); from ifsm.cli import main; raise SystemExit(main(json.loads(os.environ['IFSM_ARGS_JSON'])))"
