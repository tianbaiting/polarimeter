#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_repo_relative_or_abs(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate STEP importability and basic geometry metrics via FreeCAD/Part."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to resolve relative paths from the manifest.",
    )
    parser.add_argument(
        "--manifest",
        default="docs/reference_cad/old_version_step_manifest.json",
        help="Manifest JSON produced by build_old_version_step_manifest.py.",
    )
    parser.add_argument(
        "--output",
        default="docs/reference_cad/old_version_step_import_report.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when missing/failed STEP files are detected.",
    )
    return parser.parse_args(argv)


def _load_manifest(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Manifest root must be an object")
    entries = loaded.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Manifest must contain an 'entries' array")
    return loaded


def _as_bbox_dict(bound_box: Any) -> dict[str, float]:
    return {
        "xmin": float(bound_box.XMin),
        "xmax": float(bound_box.XMax),
        "ymin": float(bound_box.YMin),
        "ymax": float(bound_box.YMax),
        "zmin": float(bound_box.ZMin),
        "zmax": float(bound_box.ZMax),
        "xlen": float(bound_box.XLength),
        "ylen": float(bound_box.YLength),
        "zlen": float(bound_box.ZLength),
    }


def _check_entries(
    *,
    entries: list[dict[str, Any]],
    repo_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    import FreeCAD  # type: ignore  # noqa: F401
    import Part  # type: ignore

    report_entries: list[dict[str, Any]] = []
    counts = {
        "total": len(entries),
        "checked": 0,
        "missing_step": 0,
        "import_ok": 0,
        "import_failed": 0,
    }

    for item in entries:
        source_path = str(item.get("source_path", ""))
        step_path_text = str(item.get("step_path", ""))
        subsystem = str(item.get("subsystem", "unclassified"))

        step_abs = (repo_root / step_path_text).resolve()
        base_report = {
            "source_path": source_path,
            "step_path": step_path_text,
            "subsystem": subsystem,
            "import_ok": False,
            "missing_step": False,
            "volume_mm3": None,
            "bbox_mm": None,
            "solid_count": None,
            "face_count": None,
            "warnings": [],
            "error": None,
        }

        if not step_abs.exists():
            counts["missing_step"] += 1
            base_report["missing_step"] = True
            base_report["error"] = "STEP file not found"
            report_entries.append(base_report)
            continue

        counts["checked"] += 1
        try:
            shape = Part.Shape()
            shape.read(str(step_abs))
            if shape.isNull():
                counts["import_failed"] += 1
                base_report["error"] = "Loaded shape is null"
                report_entries.append(base_report)
                continue

            bbox = shape.BoundBox
            volume_mm3 = float(shape.Volume)
            solid_count = int(len(shape.Solids))
            face_count = int(len(shape.Faces))

            base_report["import_ok"] = True
            base_report["volume_mm3"] = volume_mm3
            base_report["bbox_mm"] = _as_bbox_dict(bbox)
            base_report["solid_count"] = solid_count
            base_report["face_count"] = face_count

            warnings: list[str] = base_report["warnings"]
            if volume_mm3 <= 0.0:
                warnings.append("non_positive_volume")
            if bbox.XLength <= 0.0 or bbox.YLength <= 0.0 or bbox.ZLength <= 0.0:
                warnings.append("non_positive_bbox_dimension")
            if solid_count == 0:
                warnings.append("zero_solids")

            counts["import_ok"] += 1
            report_entries.append(base_report)
        except Exception as exc:  # noqa: BLE001
            counts["import_failed"] += 1
            base_report["error"] = f"{type(exc).__name__}: {exc}"
            report_entries.append(base_report)

    return report_entries, counts


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()
    manifest_path = (repo_root / args.manifest).resolve()
    output_path = (repo_root / args.output).resolve()

    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")

    manifest = _load_manifest(manifest_path)
    manifest_entries = manifest.get("entries", [])
    assert isinstance(manifest_entries, list)

    try:
        report_entries, counts = _check_entries(entries=manifest_entries, repo_root=repo_root)
        environment_error = None
    except Exception as exc:  # noqa: BLE001
        environment_error = f"{type(exc).__name__}: {exc}"
        report_entries = []
        counts = {
            "total": len(manifest_entries),
            "checked": 0,
            "missing_step": 0,
            "import_ok": 0,
            "import_failed": 0,
        }

    payload = {
        "schema_version": "1.0",
        "generated_utc": _utc_now_iso(),
        "manifest_path": _to_repo_relative_or_abs(manifest_path, repo_root),
        "summary": counts,
        "environment_error": environment_error,
        "files": report_entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "import-report: "
        f"total={counts['total']} checked={counts['checked']} ok={counts['import_ok']} "
        f"missing={counts['missing_step']} failed={counts['import_failed']} "
        f"output={output_path.as_posix()}"
    )

    if environment_error is not None:
        return 3
    has_failure = counts["missing_step"] > 0 or counts["import_failed"] > 0
    if args.strict and has_failure:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
