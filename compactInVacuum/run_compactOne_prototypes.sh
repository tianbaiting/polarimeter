#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${TMPDIR:-/tmp}/compactOne-prototypes-freecad"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${RUNTIME_DIR}/xdg-cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${RUNTIME_DIR}/xdg-config}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export QT_OPENGL="${QT_OPENGL:-software}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export PYTHONPATH="${SCRIPT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
mkdir -p "${XDG_CACHE_HOME}/FreeCAD" "${XDG_CONFIG_HOME}/FreeCAD"

CONFIG_PATH="${1:-${SCRIPT_DIR}/config/afterSRC_compact.yaml}"
OUTPUT_DIR="${2:-${SCRIPT_DIR}/artifacts/prototypes}"
freecadcmd -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path(r'${SCRIPT_DIR}/src').resolve())); from civ.artifacts import main; raise SystemExit(main(r'${CONFIG_PATH}', r'${OUTPUT_DIR}'))"
