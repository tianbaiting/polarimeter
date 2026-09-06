from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import yaml

from ..stateflow import (
    compute_config_hash,
    load_state,
    make_state,
    save_state,
    should_skip,
)
from ..layout import build_detector_placements
from ..manifest import export_channel_manifest
from .config import load_spec
from .geometry import build_geometry
from .validation import validate_study


def now():
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def run_study(args, target, target_path, state_path, cfg, config_path, pipeline_index):
    overrides = {
        key: yaml.safe_load(value)
        for key, value in (item.split("=", 1) for item in args.set)
    }
    spec = load_spec(config_path, overrides)
    if args.dump_resolved_config:
        print(json.dumps(asdict(spec), indent=2), flush=True)
        return 0
    strict = bool(
        args.strict_validation or target.get("validation", {}).get("strict", False)
    )
    output = (target_path.parent / target["output"]["output_dir"]).resolve()
    report_path = (target_path.parent / target["artifacts"]["report_json"]).resolve()
    manifest_path = (
        target_path.parent / target["artifacts"]["channel_manifest_json"]
    ).resolve()
    sources = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(sources.rglob("*.py")):
        digest.update(str(path.relative_to(sources)).encode())
        digest.update(path.read_bytes())
    digest.update(target_path.read_bytes())
    fingerprint = compute_config_hash(
        str(config_path),
        {
            "__study_engine__": digest.hexdigest(),
            "__strict__": strict,
            "__overrides__": overrides,
        },
    )
    previous = load_state(str(state_path))
    if should_skip(previous, fingerprint) and not args.force_rebuild:
        if args.validate_only or all(
            Path(previous.get("artifacts", {}).get(k, "/nonexistent")).is_file()
            for k in ("sector_fcstd", "fcstd")
        ):
            print("skipped")
            return 0
    started = now()
    artifacts = {}
    report = None
    try:
        geometry = build_geometry(cfg, spec)
        report = validate_study(cfg, spec, geometry, strict, report_path)
        artifacts["validation_report"] = str(report_path)
        artifacts["channel_manifest"] = export_channel_manifest(
            cfg, build_detector_placements(cfg), manifest_path
        )
        if report["status"] == "pass" and not args.validate_only:
            from .artifacts import export_artifacts

            artifacts.update(
                export_artifacts(
                    cfg, spec, geometry, output, target["output"]["basename"]
                )
            )
        status = report["status"]
        state = make_state(fingerprint, status, artifacts)
        state["module"] = target["module"]
        state["run"] = {
            "status": status,
            "started_at_utc": started,
            "finished_at_utc": now(),
        }
        state["target"] = {
            "path": str(target_path),
            "pipeline_index": str(pipeline_index),
        }
        state["validation"] = {
            "status": status,
            "strict": strict,
            "report_json": str(report_path),
            "complete_modeled_extraction_certified": report[
                "complete_modeled_extraction_certified"
            ],
        }
        save_state(str(state_path), state)
        print(
            json.dumps(
                {
                    "status": status,
                    "summary": report["summary"],
                    "artifacts": artifacts,
                },
                indent=2,
            ),
            flush=True,
        )
        return 0 if status == "pass" else 1
    except Exception as exc:
        state = make_state(fingerprint, "error", artifacts)
        state["module"] = target["module"]
        state["run"] = {
            "status": "error",
            "started_at_utc": started,
            "finished_at_utc": now(),
            "error": str(exc),
        }
        state["target"] = {
            "path": str(target_path),
            "pipeline_index": str(pipeline_index),
        }
        save_state(str(state_path), state)
        raise
