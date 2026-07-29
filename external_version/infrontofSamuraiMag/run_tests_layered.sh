#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LAYER="${1:-all}"

cd "${ROOT_DIR}/.."

if [[ "${LAYER}" == "all" || "${LAYER}" == "pure_python" ]]; then
  "${PYTHON_BIN}" infrontofSamuraiMag/scripts/precheck_test_env.py --layer pure_python
  "${PYTHON_BIN}" -m pytest -q -m pure_python infrontofSamuraiMag/tests
fi

if [[ "${LAYER}" == "all" || "${LAYER}" == "freecad_runtime" ]]; then
  "${PYTHON_BIN}" infrontofSamuraiMag/scripts/precheck_test_env.py --layer freecad_runtime
  "${PYTHON_BIN}" -m pytest -q -m freecad_runtime infrontofSamuraiMag/tests
fi
