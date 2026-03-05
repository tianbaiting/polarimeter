from __future__ import annotations

import hashlib
import json
import os
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError as exc:  # pragma: no cover - only relevant for non-POSIX systems
    fcntl = None
    _FCNTL_IMPORT_ERROR = exc
else:
    _FCNTL_IMPORT_ERROR = None

try:
    import yaml
except ImportError as exc:  # pragma: no cover - mirrors config import behavior
    yaml = None
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None


SUPPORTED_TARGET_SCHEMA_VERSION = 1
TARGET_STATUS_VALUES = {"pass", "fail", "error", "skipped"}


class TargetSpecError(ValueError):
    pass


class StateLockError(RuntimeError):
    pass



def _assert_yaml_available() -> None:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for target manifest parsing. Install it with: pip install pyyaml"
        ) from _YAML_IMPORT_ERROR



def _as_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TargetSpecError(f"{field_name} must be a mapping, got {value!r}")
    return value



def _as_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TargetSpecError(f"{field_name} must be a string, got {value!r}")
    text = value.strip()
    if not text:
        raise TargetSpecError(f"{field_name} cannot be empty")
    return text



def _as_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TargetSpecError(f"{field_name} must be boolean, got {value!r}")
    return value



def _as_positive_float(value: Any, field_name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise TargetSpecError(f"{field_name} must be numeric, got {value!r}") from exc
    if out <= 0.0:
        raise TargetSpecError(f"{field_name} must be > 0, got {out}")
    return out



def _as_str_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise TargetSpecError(f"{field_name} must be a list, got {value!r}")
    out: list[str] = []
    for idx, item in enumerate(value):
        out.append(_as_str(item, f"{field_name}[{idx}]"))
    return out



def _normalize_path(path_text: str, *, base_dir: Path) -> Path:
    raw = Path(path_text).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    return (base_dir / raw).resolve()



def _normalize_target(raw: dict[str, Any], *, target_path: Path) -> dict[str, Any]:
    schema_version = raw.get("schema_version")
    if schema_version != SUPPORTED_TARGET_SCHEMA_VERSION:
        raise TargetSpecError(
            f"target.schema_version must be {SUPPORTED_TARGET_SCHEMA_VERSION}, got {schema_version!r}"
        )

    module_name = _as_str(raw.get("module"), "module")

    intent_raw = _as_mapping(raw.get("intent", {}), "intent")
    intent = {
        "description": _as_str(intent_raw.get("description", ""), "intent.description")
        if intent_raw.get("description") is not None
        else "",
    }

    build_raw = _as_mapping(raw.get("build"), "build")
    build_mode = _as_str(build_raw.get("mode", "build"), "build.mode").lower()
    if build_mode not in {"build", "validate_only"}:
        raise TargetSpecError("build.mode must be one of ['build', 'validate_only']")

    base_dir = target_path.parent
    config_path = _normalize_path(_as_str(build_raw.get("config"), "build.config"), base_dir=base_dir)

    build = {
        "config": str(config_path),
        "overrides": _as_str_list(build_raw.get("overrides", []), "build.overrides"),
        "doc_name": _as_str(build_raw.get("doc_name", module_name), "build.doc_name"),
        "mode": build_mode,
    }

    validation_raw = _as_mapping(raw.get("validation", {}), "validation")
    validation = {
        "strict": _as_bool(validation_raw.get("strict", True), "validation.strict"),
        "angle_tolerance_deg": _as_positive_float(
            validation_raw.get("angle_tolerance_deg", 0.05),
            "validation.angle_tolerance_deg",
        ),
        "radius_tolerance_mm": _as_positive_float(
            validation_raw.get("radius_tolerance_mm", 0.2),
            "validation.radius_tolerance_mm",
        ),
    }

    output_raw = _as_mapping(raw.get("output", {}), "output")
    output_dir_text = output_raw.get("output_dir")
    output_dir = _normalize_path(output_dir_text, base_dir=base_dir) if output_dir_text is not None else None

    output_formats_raw = output_raw.get("formats")
    output_formats = _as_str_list(output_formats_raw, "output.formats") if output_formats_raw is not None else None

    output = {
        "output_dir": str(output_dir) if output_dir is not None else None,
        "basename": _as_str(output_raw.get("basename"), "output.basename") if output_raw.get("basename") is not None else None,
        "formats": output_formats,
    }

    artifacts_raw = _as_mapping(raw.get("artifacts", {}), "artifacts")
    report_json_text = artifacts_raw.get("report_json")
    report_json = _normalize_path(report_json_text, base_dir=base_dir) if report_json_text is not None else None
    artifacts = {
        "report_json": str(report_json) if report_json is not None else None,
    }

    return {
        "schema_version": SUPPORTED_TARGET_SCHEMA_VERSION,
        "module": module_name,
        "intent": intent,
        "build": build,
        "validation": validation,
        "output": output,
        "artifacts": artifacts,
        "_target_path": str(target_path.resolve()),
    }



def load_target_manifest(target_path: str | Path, expected_module: str | None = None) -> dict[str, Any]:
    _assert_yaml_available()
    path = Path(target_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Target file does not exist: {path}")

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw = _as_mapping(loaded, "target")
    normalized = _normalize_target(raw, target_path=path)

    if expected_module is not None and normalized["module"] != expected_module:
        raise TargetSpecError(
            f"target.module must be {expected_module!r}, got {normalized['module']!r}"
        )

    return normalized



def canonical_target_payload(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": target["schema_version"],
        "module": target["module"],
        "intent": target.get("intent", {}),
        "build": target["build"],
        "validation": target["validation"],
        "output": target.get("output", {}),
        "artifacts": target.get("artifacts", {}),
    }



def target_sha256(target: dict[str, Any]) -> str:
    payload = canonical_target_payload(target)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()



def load_pipeline_index(index_path: str | Path, *, module_name: str) -> dict[str, Any]:
    _assert_yaml_available()
    path = Path(index_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Pipeline index does not exist: {path}")

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = _as_mapping(loaded, "pipeline_index")

    schema_version = root.get("schema_version")
    if schema_version != SUPPORTED_TARGET_SCHEMA_VERSION:
        raise TargetSpecError(
            f"pipeline_index.schema_version must be {SUPPORTED_TARGET_SCHEMA_VERSION}, got {schema_version!r}"
        )

    entries = root.get("active_modules")
    if not isinstance(entries, list):
        raise TargetSpecError("pipeline_index.active_modules must be a list")

    for idx, entry_raw in enumerate(entries):
        entry = _as_mapping(entry_raw, f"active_modules[{idx}]")
        name = _as_str(entry.get("name"), f"active_modules[{idx}].name")
        if name != module_name:
            continue

        base_dir = path.parent
        target_path = _normalize_path(_as_str(entry.get("target"), f"active_modules[{idx}].target"), base_dir=base_dir)
        state_path = _normalize_path(_as_str(entry.get("state"), f"active_modules[{idx}].state"), base_dir=base_dir)
        return {
            "name": name,
            "target": str(target_path),
            "state": str(state_path),
            "index_path": str(path),
        }

    raise TargetSpecError(f"Module {module_name!r} not found in pipeline index {path}")



def read_state_json(state_path: str | Path) -> dict[str, Any] | None:
    path = Path(state_path).expanduser().resolve()
    if not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"State file root must be a JSON object: {path}")
    return loaded



def _artifact_exists(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    path_text = entry.get("path")
    if not isinstance(path_text, str) or not path_text.strip():
        return False
    return Path(path_text).expanduser().resolve().exists()



def should_skip_build(
    previous_state: dict[str, Any] | None,
    *,
    target_hash: str,
    force_rebuild: bool,
) -> bool:
    if force_rebuild or previous_state is None:
        return False

    if previous_state.get("schema_version") != SUPPORTED_TARGET_SCHEMA_VERSION:
        return False

    target_info = previous_state.get("target")
    if not isinstance(target_info, dict) or target_info.get("sha256") != target_hash:
        return False

    run_info = previous_state.get("run")
    if not isinstance(run_info, dict) or run_info.get("status") != "pass":
        return False

    artifacts = previous_state.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        return False

    for entry in artifacts.values():
        if not _artifact_exists(entry):
            return False

    return True



def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()



def build_artifact_index(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for name, raw_path in sorted(paths.items()):
        path = raw_path.expanduser().resolve()
        exists = path.exists()
        size_bytes = path.stat().st_size if exists else None
        digest = _sha256_file(path) if exists else None
        artifacts[name] = {
            "path": str(path),
            "exists": exists,
            "size_bytes": size_bytes,
            "sha256": digest,
        }
    return artifacts



def write_state_json_atomic(state_path: str | Path, payload: dict[str, Any]) -> Path:
    path = Path(state_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.parent / f".{path.name}.tmp.{os.getpid()}"
    try:
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    return path



def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")



def build_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{os.getpid()}"



def git_head_and_dirty(repo_root: str | Path) -> tuple[str | None, bool | None]:
    root = Path(repo_root).expanduser().resolve()
    try:
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        head = head_result.stdout.strip() or None
    except (subprocess.SubprocessError, OSError):
        return None, None

    try:
        dirty_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        dirty = bool(dirty_result.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        dirty = None

    return head, dirty


@contextmanager
def state_lock(lock_path: str | Path) -> Iterator[None]:
    if fcntl is None:
        raise RuntimeError("state_lock requires fcntl on this platform") from _FCNTL_IMPORT_ERROR

    path = Path(lock_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise StateLockError(
                f"Another process already holds state lock: {path}. Retry after the current run exits."
            ) from exc

        handle.seek(0)
        handle.truncate(0)
        handle.write(str(os.getpid()))
        handle.flush()

        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
