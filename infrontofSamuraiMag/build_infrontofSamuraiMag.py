#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_SRC_DIR = _THIS_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from ifsm.cli import main


def _should_run() -> bool:
    return __name__ in {"__main__", "build_infrontofSamuraiMag"}


def _argv_for_cli() -> list[str]:
    argv = list(sys.argv[1:])
    if argv and argv[0].endswith(".py"):
        argv = argv[1:]
    return argv


if _should_run():
    raise SystemExit(main(_argv_for_cli()))
