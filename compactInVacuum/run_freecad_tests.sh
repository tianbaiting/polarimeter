#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILE="${SCRIPT_DIR}/tests/freecad_runtime.py"
freecadcmd -c "scope={'__file__': r'${TEST_FILE}', '__name__': 'freecad_runtime'}; exec(compile(open(r'${TEST_FILE}', encoding='utf-8').read(), r'${TEST_FILE}', 'exec'), scope); raise SystemExit(scope['main']())"
