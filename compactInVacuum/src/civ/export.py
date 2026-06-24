from __future__ import annotations

from pathlib import Path

import FreeCAD as App
import Part


def _shape_objects(doc: App.Document) -> list[App.DocumentObject]:
    return [obj for obj in doc.Objects if hasattr(obj, "Shape")]


def export_fcstd(doc: App.Document, output_dir: str, basename: str) -> str:
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{basename}.FCStd"
    doc.recompute()
    doc.saveAs(str(path))
    return str(path)


def export_step(doc: App.Document, output_dir: str, basename: str) -> str:
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{basename}.step"
    doc.recompute()
    objects = _shape_objects(doc)
    try:
        Part.export(objects, str(path))
    except Exception:
        import ImportGui  # pragma: no cover - exercised in FreeCAD runtime only

        ImportGui.export(objects, str(path))
    return str(path)
