from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from typing import Any

from .adapter import LocalBuildAdapter
from .config import BuildConfig, dump_snapshot_yaml
from .layout import front_face_center
from .stateflow import (
    SUPPORTED_TARGET_SCHEMA_VERSION,
    build_artifact_index,
    build_run_id,
    git_head_and_dirty,
    load_pipeline_index,
    load_target_manifest,
    read_state_json,
    should_skip_build,
    state_lock,
    target_sha256,
    utc_now_iso,
    write_state_json_atomic,
)
from .validation import ValidationThresholds, write_report_json


MODULE_NAME = "infrontofSamuraiMag"
_ALLOWED_OUTPUT_FORMATS = {"fcstd", "step"}



def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "default_infront.yaml"



def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]



def _parse_formats(raw: str) -> tuple[str, ...]:
    parts = tuple(token.strip().lower() for token in raw.split(",") if token.strip())
    if not parts:
        raise ValueError("--formats cannot be empty")
    return parts



def _apply_cli_output_overrides(cfg: BuildConfig, args: argparse.Namespace) -> BuildConfig:
    updated = cfg
    if args.output_dir is not None:
        updated = replace(updated, output=replace(updated.output, output_dir=args.output_dir.resolve()))
    if args.basename is not None:
        updated = replace(updated, output=replace(updated.output, basename=args.basename))
    if args.formats is not None:
        updated = replace(updated, output=replace(updated.output, formats=_parse_formats(args.formats)))
    return updated



def _apply_target_output_overrides(cfg: BuildConfig, target: dict[str, Any]) -> BuildConfig:
    updated = cfg
    output = target.get("output", {})
    if not isinstance(output, dict):
        return updated

    output_dir_text = output.get("output_dir")
    if isinstance(output_dir_text, str) and output_dir_text.strip():
        updated = replace(updated, output=replace(updated.output, output_dir=Path(output_dir_text).expanduser().resolve()))

    basename = output.get("basename")
    if isinstance(basename, str) and basename.strip():
        updated = replace(updated, output=replace(updated.output, basename=basename.strip()))

    formats = output.get("formats")
    if isinstance(formats, list) and formats:
        parsed_formats = tuple(str(item).strip().lower() for item in formats if str(item).strip())
        for fmt in parsed_formats:
            if fmt not in _ALLOWED_OUTPUT_FORMATS:
                raise ValueError(f"Unsupported output format {fmt!r}, allowed: {sorted(_ALLOWED_OUTPUT_FORMATS)}")
        updated = replace(
            updated,
            output=replace(updated.output, formats=parsed_formats),
        )

    return updated



def _resolve_report_path(cfg: BuildConfig, report_path: Path | None) -> Path:
    if report_path is not None:
        return report_path.expanduser().resolve()
    return (cfg.output.output_dir / f"{cfg.output.basename}.validation_report.json").resolve()



def _resolve_target_report_path(
    cfg: BuildConfig,
    *,
    cli_report_path: Path | None,
    target: dict[str, Any],
) -> Path:
    if cli_report_path is not None:
        return cli_report_path.expanduser().resolve()

    artifacts = target.get("artifacts", {})
    if isinstance(artifacts, dict):
        report_text = artifacts.get("report_json")
        if isinstance(report_text, str) and report_text.strip():
            return Path(report_text).expanduser().resolve()

    return _resolve_report_path(cfg, None)



def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate infrontofSamuraiMag FreeCAD model from modular YAML config.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=_default_config_path(),
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override config value by dotted key, e.g. geometry.beam.outlet.shape=square",
    )
    parser.add_argument("--output-dir", type=Path, default=None, help="Override output.dir")
    parser.add_argument("--basename", type=str, default=None, help="Override output.basename")
    parser.add_argument("--formats", type=str, default=None, help="Override output.formats, comma-separated")
    parser.add_argument(
        "--dump-resolved-config",
        action="store_true",
        help="Print merged and validated config snapshot before build.",
    )
    parser.add_argument("--doc-name", type=str, default=None, help="FreeCAD document name")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Skip CAD generation/export and run only layout/constraint validation.",
    )
    parser.add_argument(
        "--strict-validation",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Return non-zero when validation fails.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Write validation report JSON to this path (default: output_dir/basename.validation_report.json).",
    )
    parser.add_argument(
        "--angle-tol-deg",
        type=float,
        default=None,
        help="Maximum allowed absolute detector angle error in degrees.",
    )
    parser.add_argument(
        "--radius-tol-mm",
        type=float,
        default=None,
        help="Maximum allowed absolute detector front-center radius error in mm.",
    )
    parser.add_argument(
        "--target-file",
        type=Path,
        default=None,
        help="Stateful execution target YAML path.",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="State JSON path used for stateful execution.",
    )
    parser.add_argument(
        "--pipeline-index",
        type=Path,
        default=None,
        help="Root pipeline index YAML used to resolve module target/state paths.",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Ignore skip checks and force a new build/validation run.",
    )
    return parser.parse_args(argv)



def _print_channel_summary(report_dict: dict[str, object]) -> None:
    channels = report_dict.get("channels", [])
    if not isinstance(channels, list):
        return
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        print(
            f"{channel['tag']}: target_angle={channel['target_angle_deg']:.3f} deg "
            f"actual_angle={channel['actual_angle_deg']:.3f} deg delta_angle={channel['delta_angle_deg']:.4f} deg "
            f"target_radius={channel['target_radius_mm']:.3f} mm actual_radius={channel['actual_radius_mm']:.3f} mm "
            f"delta_radius={channel['delta_radius_mm']:.4f} mm pass={channel['pass']}"
        )



def _print_subsystem_summary(report_dict: dict[str, object]) -> None:
    subsystems = report_dict.get("subsystems", {})
    if not isinstance(subsystems, dict):
        return
    for name, entry in sorted(subsystems.items()):
        if not isinstance(entry, dict):
            continue
        status = entry.get("status", "unknown")
        checks = entry.get("checks", [])
        failed = 0
        if isinstance(checks, list):
            failed = sum(0 if isinstance(check, dict) and check.get("pass", False) else 1 for check in checks)
        print(f"Subsystem {name}: status={status} failed_checks={failed}")



def _ensure_positive_thresholds(angle_tol_deg: float, radius_tol_mm: float) -> None:
    if angle_tol_deg <= 0.0:
        raise ValueError("--angle-tol-deg must be > 0")
    if radius_tol_mm <= 0.0:
        raise ValueError("--radius-tol-mm must be > 0")



def _run_build_pipeline(
    *,
    adapter: LocalBuildAdapter,
    cfg: BuildConfig,
    doc_name: str,
    validate_only: bool,
    angle_tol_deg: float,
    radius_tol_mm: float,
    report_path: Path,
) -> tuple[int, dict[str, Path], Path, str]:
    exported_paths: dict[str, Path] = {}

    if validate_only:
        placements = adapter.build_layout_only(cfg)
    else:
        result = adapter.build_model(cfg, doc_name=doc_name)
        exported_paths = adapter.export_model(result, cfg.output)
        placements = result.placements

        for placement in placements:
            center = front_face_center(placement)
            print(
                f"{placement.tag}: angle={placement.angle_deg:.3f} deg radius={placement.radius_mm:.3f} mm "
                f"front_center=({center.x:.3f}, {center.y:.3f}, {center.z:.3f})"
            )

    thresholds = ValidationThresholds(
        angle_tolerance_deg=angle_tol_deg,
        radius_tolerance_mm=radius_tol_mm,
    )
    report = adapter.validate_constraints(cfg, placements, thresholds)

    artifacts = {fmt: str(path) for fmt, path in sorted(exported_paths.items())}
    report_path = write_report_json(report, report_path, artifacts=artifacts)

    report_dict = {
        "status": report.status,
        "channels": [
            {
                "tag": item.tag,
                "target_angle_deg": item.target_angle_deg,
                "actual_angle_deg": item.actual_angle_deg,
                "delta_angle_deg": item.delta_angle_deg,
                "target_radius_mm": item.target_radius_mm,
                "actual_radius_mm": item.actual_radius_mm,
                "delta_radius_mm": item.delta_radius_mm,
                "pass": item.passed,
            }
            for item in report.channels
        ],
        "subsystems": {
            subsystem.name: {
                "status": subsystem.status,
                "checks": [
                    {
                        "name": check.name,
                        "pass": check.passed,
                        "detail": check.detail,
                    }
                    for check in subsystem.checks
                ],
            }
            for subsystem in report.subsystems
        },
    }

    _print_channel_summary(report_dict)
    _print_subsystem_summary(report_dict)

    for fmt, path in sorted(exported_paths.items()):
        print(f"Saved {fmt}: {path}")
    print(f"Saved validation_report: {report_path}")
    print(f"Validation status: {report.status}")

    return (2 if report.status != "pass" else 0), exported_paths, report_path, report.status



def _default_doc_name() -> str:
    return MODULE_NAME



def _build_state_payload(
    *,
    module_name: str,
    target_path: Path,
    target_hash: str,
    run_id: str,
    started_at_utc: str,
    finished_at_utc: str,
    run_status: str,
    git_head: str | None,
    git_dirty: bool | None,
    strict_validation: bool,
    angle_tol_deg: float,
    radius_tol_mm: float,
    validation_status: str | None,
    report_path: Path | None,
    artifacts: dict[str, dict[str, Any]],
    error: str | None = None,
) -> dict[str, Any]:
    if run_status not in {"pass", "fail", "error", "skipped"}:
        raise ValueError(f"Unsupported run_status: {run_status}")

    run_block: dict[str, Any] = {
        "run_id": run_id,
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "status": run_status,
        "git_head": git_head,
        "git_dirty": git_dirty,
    }
    if error is not None:
        run_block["error"] = error

    validation_block: dict[str, Any] = {
        "status": validation_status,
        "strict": strict_validation,
        "angle_tolerance_deg": angle_tol_deg,
        "radius_tolerance_mm": radius_tol_mm,
        "report_json": str(report_path) if report_path is not None else None,
    }

    return {
        "schema_version": SUPPORTED_TARGET_SCHEMA_VERSION,
        "module": module_name,
        "target": {
            "path": str(target_path.expanduser().resolve()),
            "sha256": target_hash,
        },
        "run": run_block,
        "validation": validation_block,
        "artifacts": artifacts,
    }



def _resolve_target_and_state(args: argparse.Namespace) -> tuple[Path | None, Path | None]:
    target_path = args.target_file.expanduser().resolve() if args.target_file is not None else None
    state_path = args.state_file.expanduser().resolve() if args.state_file is not None else None

    if args.pipeline_index is None:
        if target_path is None and state_path is not None:
            raise ValueError("--state-file requires --target-file or --pipeline-index")
        if target_path is None and args.force_rebuild:
            raise ValueError("--force-rebuild requires --target-file or --pipeline-index")
        return target_path, state_path

    module_entry = load_pipeline_index(args.pipeline_index, module_name=MODULE_NAME)

    if target_path is None:
        target_path = Path(module_entry["target"]).expanduser().resolve()
    if state_path is None:
        state_path = Path(module_entry["state"]).expanduser().resolve()

    return target_path, state_path



def _run_legacy_mode(args: argparse.Namespace) -> int:
    strict_validation = True if args.strict_validation is None else args.strict_validation
    angle_tol_deg = 0.05 if args.angle_tol_deg is None else args.angle_tol_deg
    radius_tol_mm = 0.2 if args.radius_tol_mm is None else args.radius_tol_mm
    _ensure_positive_thresholds(angle_tol_deg, radius_tol_mm)

    adapter = LocalBuildAdapter()

    cfg = adapter.load_config(args.config, overrides=args.set)
    cfg = _apply_cli_output_overrides(cfg, args)

    if args.dump_resolved_config:
        print(dump_snapshot_yaml(cfg))

    doc_name = args.doc_name or _default_doc_name()
    report_path = _resolve_report_path(cfg, args.report_json)

    validation_exit_code, _, _, _ = _run_build_pipeline(
        adapter=adapter,
        cfg=cfg,
        doc_name=doc_name,
        validate_only=args.validate_only,
        angle_tol_deg=angle_tol_deg,
        radius_tol_mm=radius_tol_mm,
        report_path=report_path,
    )

    if strict_validation:
        return validation_exit_code
    return 0



def _run_target_mode(args: argparse.Namespace, *, target_path: Path, state_path: Path | None) -> int:
    adapter = LocalBuildAdapter()
    target = load_target_manifest(target_path, expected_module=MODULE_NAME)
    target_hash = target_sha256(target)

    effective_state_path = state_path or (target_path.parent / "state.json")
    lock_path = effective_state_path.with_name("state.lock")

    validation_cfg = target["validation"]
    strict_validation = validation_cfg["strict"] if args.strict_validation is None else args.strict_validation
    angle_tol_deg = validation_cfg["angle_tolerance_deg"] if args.angle_tol_deg is None else args.angle_tol_deg
    radius_tol_mm = validation_cfg["radius_tolerance_mm"] if args.radius_tol_mm is None else args.radius_tol_mm
    _ensure_positive_thresholds(angle_tol_deg, radius_tol_mm)

    started_at = utc_now_iso()
    run_id = build_run_id()
    git_head, git_dirty = git_head_and_dirty(_repo_root())

    with state_lock(lock_path):
        previous_state = read_state_json(effective_state_path)

        if should_skip_build(previous_state, target_hash=target_hash, force_rebuild=args.force_rebuild):
            finished_at = utc_now_iso()
            prior_validation = previous_state.get("validation", {}) if isinstance(previous_state, dict) else {}
            prior_artifacts = previous_state.get("artifacts", {}) if isinstance(previous_state, dict) else {}

            payload = _build_state_payload(
                module_name=MODULE_NAME,
                target_path=target_path,
                target_hash=target_hash,
                run_id=run_id,
                started_at_utc=started_at,
                finished_at_utc=finished_at,
                run_status="skipped",
                git_head=git_head,
                git_dirty=git_dirty,
                strict_validation=bool(prior_validation.get("strict", strict_validation)),
                angle_tol_deg=float(prior_validation.get("angle_tolerance_deg", angle_tol_deg)),
                radius_tol_mm=float(prior_validation.get("radius_tolerance_mm", radius_tol_mm)),
                validation_status=prior_validation.get("status", "pass"),
                report_path=Path(prior_validation["report_json"]).expanduser().resolve()
                if isinstance(prior_validation.get("report_json"), str)
                else None,
                artifacts=prior_artifacts if isinstance(prior_artifacts, dict) else {},
            )
            write_state_json_atomic(effective_state_path, payload)
            print(f"Skipped build: unchanged target hash and valid artifacts ({target_hash[:12]}...).")
            print(f"Saved state: {effective_state_path}")
            return 0

        report_path: Path | None = None
        try:
            build_cfg = target["build"]
            cfg = adapter.load_config(Path(build_cfg["config"]), overrides=build_cfg["overrides"])
            cfg = _apply_target_output_overrides(cfg, target)
            cfg = _apply_cli_output_overrides(cfg, args)

            if args.dump_resolved_config:
                print(dump_snapshot_yaml(cfg))

            doc_name = args.doc_name or build_cfg["doc_name"]
            validate_only = args.validate_only or (build_cfg["mode"] == "validate_only")
            report_path = _resolve_target_report_path(cfg, cli_report_path=args.report_json, target=target)

            validation_exit_code, exported_paths, report_path, validation_status = _run_build_pipeline(
                adapter=adapter,
                cfg=cfg,
                doc_name=doc_name,
                validate_only=validate_only,
                angle_tol_deg=angle_tol_deg,
                radius_tol_mm=radius_tol_mm,
                report_path=report_path,
            )

            artifact_paths = {fmt: path for fmt, path in exported_paths.items()}
            artifact_paths["validation_report"] = report_path
            artifacts = build_artifact_index(artifact_paths)

            finished_at = utc_now_iso()
            run_status = "pass" if validation_status == "pass" else "fail"
            payload = _build_state_payload(
                module_name=MODULE_NAME,
                target_path=target_path,
                target_hash=target_hash,
                run_id=run_id,
                started_at_utc=started_at,
                finished_at_utc=finished_at,
                run_status=run_status,
                git_head=git_head,
                git_dirty=git_dirty,
                strict_validation=strict_validation,
                angle_tol_deg=angle_tol_deg,
                radius_tol_mm=radius_tol_mm,
                validation_status=validation_status,
                report_path=report_path,
                artifacts=artifacts,
            )
            write_state_json_atomic(effective_state_path, payload)
            print(f"Saved state: {effective_state_path}")

            if strict_validation:
                return validation_exit_code
            return 0

        except Exception as exc:
            finished_at = utc_now_iso()
            payload = _build_state_payload(
                module_name=MODULE_NAME,
                target_path=target_path,
                target_hash=target_hash,
                run_id=run_id,
                started_at_utc=started_at,
                finished_at_utc=finished_at,
                run_status="error",
                git_head=git_head,
                git_dirty=git_dirty,
                strict_validation=strict_validation,
                angle_tol_deg=angle_tol_deg,
                radius_tol_mm=radius_tol_mm,
                validation_status="error",
                report_path=report_path,
                artifacts={},
                error=str(exc),
            )
            write_state_json_atomic(effective_state_path, payload)
            print(f"Saved state: {effective_state_path}")
            raise



def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    target_path, state_path = _resolve_target_and_state(args)
    if target_path is None:
        return _run_legacy_mode(args)

    return _run_target_mode(args, target_path=target_path, state_path=state_path)
