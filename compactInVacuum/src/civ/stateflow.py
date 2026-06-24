from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


MODULE_NAME = "compactInVacuum"
SCHEMA_VERSION = 1
_PASS_STATUSES = {"pass", "skipped"}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def compute_config_hash(cfg_path: str, overrides: dict) -> str:
    path = Path(cfg_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    payload = {
        "module": MODULE_NAME,
        "config_path": str(path),
        "config_sha256": _sha256_bytes(path.read_bytes()),
        "overrides": {key: overrides[key] for key in sorted(overrides)},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256_bytes(encoded)


def load_state(state_path: str) -> dict:
    path = Path(state_path).expanduser().resolve()
    if not path.exists():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"State file root must be a JSON object: {path}")
    return loaded


def save_state(state_path: str, state: dict) -> None:
    path = Path(state_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp.{os.getpid()}"
    try:
        tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def should_skip(state: dict, current_hash: str) -> bool:
    if not state:
        return False
    state_hash = state.get("config_hash")
    if state_hash != current_hash:
        return False

    run_info = state.get("run")
    if isinstance(run_info, dict):
        run_status = run_info.get("status")
    else:
        run_status = state.get("status")
    if run_status != "pass":
        return False

    validation = state.get("validation")
    if isinstance(validation, dict):
        validation_status = validation.get("status")
        if validation_status not in (None, "pass"):
            return False

    return True


def make_state(hash: str, status: str, artifacts: dict) -> dict:
    if status not in {"pass", "fail", "error", "skipped"}:
        raise ValueError(f"Unsupported status: {status}")
    return {
        "schema_version": SCHEMA_VERSION,
        "module": MODULE_NAME,
        "config_hash": hash,
        "run": {"status": status},
        "artifacts": artifacts,
    }
