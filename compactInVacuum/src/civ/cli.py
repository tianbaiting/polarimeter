from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - import guard
    yaml = None
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

from .config import CIVConfig, dump_config_yaml, load_config
from .layout import build_detector_placements
from .stateflow import compute_config_hash, load_state, make_state, save_state, should_skip
from .validation import validate_assembly


MODULE_NAME = os.environ.get("CIV_MODULE_NAME", "compactInVacuum").strip() or "compactInVacuum"


def _assert_yaml_available() -> None:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for compactInVacuum target parsing. Install it with: pip install pyyaml"
        ) from _YAML_IMPORT_ERROR


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_pipeline_index() -> Path:
    return _repo_root() / "codex_targets.yaml"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the compactInVacuum polarimeter variant.")
    parser.add_argument("--pipeline-index", type=Path, default=_default_pipeline_index())
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--strict-validation", action="store_true")
    parser.add_argument("--force-rebuild", action="store_true")
    parser.add_argument("--dump-resolved-config", action="store_true")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    return parser.parse_args(argv)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    _assert_yaml_available()
    if not path.exists():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected YAML mapping at {path}")
    return loaded


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def _resolve_pipeline_entry(index_path: Path) -> tuple[Path, Path]:
    root = _load_yaml_file(index_path)
    entries = root.get("active_modules")
    if entries is None:
        entries = root.get("modules")
    if not isinstance(entries, list):
        raise ValueError(f"Pipeline index must define active_modules or modules list: {index_path}")

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("name") != MODULE_NAME:
            continue
        target_path = _resolve_path(index_path.parent, str(entry["target"]))
        state_path = _resolve_path(index_path.parent, str(entry["state"]))
        return target_path, state_path

    raise ValueError(f"Module {MODULE_NAME!r} not found in pipeline index {index_path}")


def _parse_overrides(items: list[str]) -> dict[str, Any]:
    _assert_yaml_available()
    overrides: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid override syntax: {item!r}. Expected KEY=VALUE")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid override syntax: {item!r}. Empty key")
        overrides[key] = yaml.safe_load(raw_value)
    return overrides


def _load_target(target_path: Path) -> dict[str, Any]:
    target = _load_yaml_file(target_path)
    module_name = target.get("module")
    if module_name != MODULE_NAME:
        raise ValueError(f"target.module must be {MODULE_NAME!r}, got {module_name!r}")
    return target


def _effective_strict(target: dict[str, Any], force_strict: bool) -> bool:
    validation = target.get("validation", {})
    strict = False
    if isinstance(validation, dict):
        strict = bool(validation.get("strict", False))
    return force_strict or strict


def _apply_target_doc_name(cfg: CIVConfig, target: dict[str, Any]) -> CIVConfig:
    build = target.get("build", {})
    if isinstance(build, dict):
        doc_name = build.get("doc_name")
        if isinstance(doc_name, str) and doc_name.strip():
            return replace(cfg, doc_name=doc_name.strip())
    return cfg


def _output_dir(target: dict[str, Any], target_path: Path) -> Path:
    output = target.get("output", {})
    if not isinstance(output, dict):
        return target_path.parent.resolve()
    output_dir = output.get("output_dir", ".")
    return _resolve_path(target_path.parent, str(output_dir))


def _basename(target: dict[str, Any]) -> str:
    output = target.get("output", {})
    if isinstance(output, dict):
        basename = output.get("basename")
        if isinstance(basename, str) and basename.strip():
            return basename.strip()
    return MODULE_NAME


def _formats(target: dict[str, Any]) -> tuple[str, ...]:
    output = target.get("output", {})
    if isinstance(output, dict):
        formats = output.get("formats")
        if isinstance(formats, list) and formats:
            return tuple(str(item).strip().lower() for item in formats if str(item).strip())
    return ("fcstd", "step")


def _report_path(target: dict[str, Any], target_path: Path, output_dir: Path, basename: str) -> Path:
    artifacts = target.get("artifacts", {})
    if isinstance(artifacts, dict):
        report_json = artifacts.get("report_json")
        if isinstance(report_json, str) and report_json.strip():
            return _resolve_path(target_path.parent, report_json)
    return (output_dir / f"{basename}.validation_report.json").resolve()


def _channel_manifest_path(
    target: dict[str, Any],
    target_path: Path,
    output_dir: Path,
    basename: str,
) -> Path:
    artifacts = target.get("artifacts", {})
    if isinstance(artifacts, dict):
        manifest_json = artifacts.get("channel_manifest_json")
        if isinstance(manifest_json, str) and manifest_json.strip():
            return _resolve_path(target_path.parent, manifest_json)
    return (output_dir / f"{basename}.channel_manifest.json").resolve()


def _status_exit_code(status: str, strict: bool) -> int:
    _ = strict
    return 0 if status == "pass" else 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pipeline_index = args.pipeline_index.expanduser().resolve()
    target_path, state_path = _resolve_pipeline_entry(pipeline_index)
    target = _load_target(target_path)
    overrides = _parse_overrides(args.set)

    build_cfg = target.get("build", {})
    if not isinstance(build_cfg, dict):
        raise ValueError("target.build must be a mapping")
    config_path = _resolve_path(target_path.parent, str(build_cfg["config"]))

    cfg = load_config(str(config_path), overrides=overrides)
    cfg = _apply_target_doc_name(cfg, target)

    if args.dump_resolved_config:
        print(dump_config_yaml(cfg), end="")
        return 0

    strict = _effective_strict(target, args.strict_validation)
    output_dir = _output_dir(target, target_path)
    basename = _basename(target)
    formats = _formats(target)
    report_path = _report_path(target, target_path, output_dir, basename)
    channel_manifest_path = _channel_manifest_path(target, target_path, output_dir, basename)
    hash_inputs = {
        **overrides,
        "__validation.strict__": strict,
        "__target.module__": MODULE_NAME,
    }
    current_hash = compute_config_hash(str(config_path), hash_inputs)
    previous_state = load_state(str(state_path))
    if should_skip(previous_state, current_hash) and not args.force_rebuild:
        print("skipped")
        return 0

    started_at = _utc_now()
    report: dict[str, Any] | None = None
    artifacts: dict[str, Any] = {}

    try:
        placements = build_detector_placements(cfg)
        report = validate_assembly(cfg, placements, strict, output_path=report_path)
        artifacts["validation_report"] = str(report_path)
        from .manifest import export_channel_manifest

        artifacts["channel_manifest"] = export_channel_manifest(
            cfg,
            placements,
            channel_manifest_path,
        )

        validate_only = args.validate_only or str(build_cfg.get("mode", "build")).lower() == "validate_only"
        if not validate_only and report["status"] == "pass":
            from .assembly import build_assembly, build_compact_one_document
            from .artifacts import document_geometry_metrics
            from .export import export_fcstd, export_step

            doc = (
                build_compact_one_document(cfg)
                if cfg.compact_one is not None
                else build_assembly(cfg)
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            if "fcstd" in formats:
                artifacts["fcstd"] = export_fcstd(doc, str(output_dir), basename)
            if "step" in formats:
                artifacts["step"] = export_step(doc, str(output_dir), basename)
            metrics_path = output_dir / f"{basename}.geometry_metrics.json"
            metrics_path.write_text(
                json.dumps(
                    document_geometry_metrics(
                        cfg,
                        doc,
                        "deployment_assembly",
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            artifacts["geometry_metrics"] = str(metrics_path)

        status = report["status"]
        state = make_state(current_hash, status, artifacts)
        state["target"] = {
            "path": str(target_path),
            "pipeline_index": str(pipeline_index),
        }
        state["run"] = {
            "status": status,
            "started_at_utc": started_at,
            "finished_at_utc": _utc_now(),
        }
        state["validation"] = {
            "status": status,
            "strict": strict,
            "report_json": str(report_path),
            "angle_tolerance_deg": cfg.validation.angle_tolerance_deg,
            "radius_tolerance_mm": cfg.validation.radius_tolerance_mm,
        }
        save_state(str(state_path), state)
        print(f"validation_report: {report_path}")
        for name, path in sorted(artifacts.items()):
            if name == "validation_report":
                continue
            print(f"{name}: {path}")
        print(f"status: {status}")
        return _status_exit_code(status, strict)

    except Exception as exc:
        error_state = make_state(current_hash, "error", artifacts)
        error_state["target"] = {
            "path": str(target_path),
            "pipeline_index": str(pipeline_index),
        }
        error_state["run"] = {
            "status": "error",
            "started_at_utc": started_at,
            "finished_at_utc": _utc_now(),
            "error": str(exc),
        }
        if report is not None:
            error_state["validation"] = {
                "status": report.get("status", "error"),
                "strict": strict,
                "report_json": str(report_path),
            }
        save_state(str(state_path), error_state)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
