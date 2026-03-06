#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


SOLIDWORKS_EXTENSIONS = {".sldprt", ".sldasm"}


@dataclass(frozen=True)
class ManifestEntry:
    source_path: str
    step_path: str
    subsystem: str
    units_mm: bool
    status: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_repo_relative_or_abs(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_solidworks_files(source_root: Path) -> list[Path]:
    items: list[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in SOLIDWORKS_EXTENSIONS:
            items.append(path)
    items.sort()
    return items


def _detect_subsystem(source_rel: Path) -> str:
    joined = "/".join(part.lower() for part in source_rel.parts)
    name = source_rel.stem.lower()

    if "scintilator" in joined or any(token in name for token in ("detector", "pmt", "jiazi")):
        return "detector"
    if any(token in name for token in ("板", "plate", "hvv")):
        return "plates"
    if any(token in name for token in ("靶", "target")):
        return "target"
    if any(token in name for token in ("chamber", "conepipe", "nozzle")):
        return "chamber"
    if any(token in name for token in ("base", "stand")):
        return "stand"
    if any(token in name for token in ("all", "system", "assembly")) or source_rel.suffix.lower() == ".sldasm":
        return "assembly"
    return "unclassified"


def _build_entries(
    source_root: Path,
    step_root: Path,
    repo_root: Path,
) -> list[ManifestEntry]:
    entries: list[ManifestEntry] = []
    for source_abs in _iter_solidworks_files(source_root):
        source_rel = source_abs.relative_to(repo_root)
        source_rel_from_source_root = source_abs.relative_to(source_root)
        step_rel_path = source_rel_from_source_root.with_suffix(".step")
        step_abs = step_root / step_rel_path
        step_rel = _to_repo_relative_or_abs(step_abs, repo_root)
        status = "present" if step_abs.exists() else "missing"
        entries.append(
            ManifestEntry(
                source_path=source_rel.as_posix(),
                step_path=step_rel,
                subsystem=_detect_subsystem(source_rel_from_source_root),
                units_mm=True,
                status=status,
            )
        )
    return entries


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build SolidWorks->STEP manifest for old-version CAD reference migration."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root path used for relative-path serialization.",
    )
    parser.add_argument(
        "--source-root",
        default="old-version",
        help="Root directory that contains SolidWorks files (*.SLDPRT/*.SLDASM).",
    )
    parser.add_argument(
        "--step-root",
        default="docs/reference_cad/old_version_step",
        help="Root directory containing converted STEP files.",
    )
    parser.add_argument(
        "--output",
        default="docs/reference_cad/old_version_step_manifest.json",
        help="Output manifest JSON path.",
    )
    parser.add_argument(
        "--fail-on-missing-step",
        action="store_true",
        help="Exit with code 2 when one or more expected STEP files are missing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()
    source_root = (repo_root / args.source_root).resolve()
    step_root = (repo_root / args.step_root).resolve()
    output_path = (repo_root / args.output).resolve()

    if not source_root.exists():
        raise FileNotFoundError(f"source-root not found: {source_root}")
    if not source_root.is_dir():
        raise NotADirectoryError(f"source-root must be a directory: {source_root}")

    entries = _build_entries(source_root, step_root, repo_root)
    present_count = sum(1 for item in entries if item.status == "present")
    missing_count = sum(1 for item in entries if item.status == "missing")

    payload = {
        "schema_version": "1.0",
        "generated_utc": _utc_now_iso(),
        "source_root": _to_repo_relative_or_abs(source_root, repo_root),
        "step_root": _to_repo_relative_or_abs(step_root, repo_root),
        "summary": {
            "solidworks_files": len(entries),
            "step_present": present_count,
            "step_missing": missing_count,
        },
        "entries": [asdict(item) for item in entries],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "manifest: "
        f"files={len(entries)} present={present_count} missing={missing_count} output={output_path.as_posix()}"
    )

    if args.fail_on_missing_step and missing_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
