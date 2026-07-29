from __future__ import annotations

from pathlib import Path

import FreeCAD as App
import Part


def _shape_objects(doc: App.Document) -> list[App.DocumentObject]:
    exported: list[App.DocumentObject] = []
    for obj in doc.Objects:
        if obj.TypeId == "App::DocumentObjectGroup" or not hasattr(obj, "Shape"):
            continue
        if hasattr(obj, "EngineeringRole") and str(obj.EngineeringRole) not in {
            "physical",
            "purchased_component_interface",
        }:
            continue
        exported.append(obj)
    # [EN] STEP is the physical exchange artifact; engineering overlays remain available in FCStd and JSON without becoming manufactured solids. / [CN] STEP 是物理交换工件；工程叠加层保留在 FCStd 和 JSON 中，不会变成制造实体。
    return exported


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
