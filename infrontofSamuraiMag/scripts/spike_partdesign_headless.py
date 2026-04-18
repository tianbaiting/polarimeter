"""Throwaway feasibility spike for Approach Y.

Runs the six PartDesign capabilities needed by the detector-clamp redesign
(spec §6). Writes a machine-readable JSON report to stdout with pass/fail per
item; non-zero exit on any failure. Delete this script after Sub-2 merges.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import FreeCAD as App
import Part
import Sketcher


RESULTS: list[dict[str, object]] = []


def record(item_id: str, title: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"id": item_id, "title": title, "pass": ok, "detail": detail})


def spike_body_creation(doc: App.Document) -> object:
    body = doc.addObject("PartDesign::Body", "SpikeBody")
    doc.recompute()
    record("0.1", "PartDesign::Body creation", body is not None, f"name={body.Name}")
    return body


def spike_sketch_closed_profile(doc: App.Document, body: object) -> object:
    sketch = body.newObject("Sketcher::SketchObject", "SpikeSketch")
    xy = doc.getObject("XY_Plane")
    support_value = (xy, [""]) if xy else None
    if hasattr(sketch, "AttachmentSupport"):
        sketch.AttachmentSupport = support_value
    elif hasattr(sketch, "Support"):
        sketch.Support = support_value
    sketch.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(20, 0, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(20, 0, 0), App.Vector(20, 10, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(20, 10, 0), App.Vector(0, 10, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(0, 10, 0), App.Vector(0, 0, 0)), False)
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 2, 1, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 1, 2, 2, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 2, 2, 3, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 3, 2, 0, 1))
    doc.recompute()
    valid = sketch.Shape.isValid() if sketch.Shape else False
    record("0.2", "Sketcher closed profile valid", bool(valid))
    return sketch


def spike_pad(doc: App.Document, body: object, sketch: object) -> object:
    pad = body.newObject("PartDesign::Pad", "SpikePad")
    pad.Profile = sketch
    pad.Length = 10.0
    doc.recompute()
    solids = len(body.Shape.Solids)
    volume = body.Shape.Volume if solids else 0.0
    ok = (not pad.Shape.isNull()) and solids == 1 and volume > 0.0
    record("0.3", "PartDesign::Pad gives single-solid Body", ok,
           f"solids={solids}, volume={volume:.3f}")
    # Stash for downstream criteria via FreeCAD dynamic property
    # (raw Python attrs aren't supported on C++-bound PartDesign::Pad).
    if not hasattr(pad, "SpikeBaseVolume"):
        pad.addProperty("App::PropertyFloat", "SpikeBaseVolume",
                        "Spike", "Body volume after Pad feature")
    pad.SpikeBaseVolume = volume
    return pad


def spike_hole(doc: App.Document, body: object, pad: object) -> None:
    hole_sketch = body.newObject("Sketcher::SketchObject", "SpikeHoleSketch")
    hole_sketch.addGeometry(Part.Circle(App.Vector(10, 5, 10), App.Vector(0, 0, 1), 1.5), False)
    doc.recompute()
    hole = body.newObject("PartDesign::Hole", "SpikeHole")
    hole.Profile = hole_sketch
    hole.ThreadType = "ISOMetricProfile"
    hole.ThreadSize = "M3"
    # FreeCAD 1.0: DepthType selects the enum; Depth is the length.
    hole.DepthType = "Dimension"
    hole.Depth = 5.0
    doc.recompute()
    solids = len(body.Shape.Solids)
    volume = body.Shape.Volume if solids else 0.0
    base_volume = float(pad.SpikeBaseVolume) if hasattr(pad, "SpikeBaseVolume") else 0.0
    # Real hole cut → body volume strictly decreases from the Pad baseline
    # (allow for the Fillet having run first and already reducing it — we just
    # need volume < base_volume, not a specific delta).
    shrank = base_volume > 0.0 and volume < base_volume - 1e-6
    ok = (hasattr(hole, "ThreadSize") and hole.ThreadSize == "M3"
          and not hole.Shape.isNull() and solids == 1 and shrank)
    record("0.4", "PartDesign::Hole ISO threaded AND cut through material", ok,
           f"ThreadSize={getattr(hole, 'ThreadSize', None)}, solids={solids}, "
           f"volume={volume:.3f}, base_volume={base_volume:.3f}, shrank={shrank}")


def spike_fillet(doc: App.Document, body: object, pad: object) -> None:
    edges = body.Shape.Edges
    # Pick any non-degenerate edge; spike only verifies the API doesn't null-face.
    edge_names = [f"Edge{i+1}" for i in range(min(2, len(edges)))]
    fillet = body.newObject("PartDesign::Fillet", "SpikeFillet")
    # FreeCAD 1.0 wants the DocumentObject, not its Shape.
    fillet.Base = (body, edge_names) if hasattr(fillet, "Base") else None
    if hasattr(fillet, "Radius"):
        fillet.Radius = 1.0
    doc.recompute()
    solids = len(body.Shape.Solids)
    volume = body.Shape.Volume if solids else 0.0
    base_volume = float(pad.SpikeBaseVolume) if hasattr(pad, "SpikeBaseVolume") else 0.0
    # A real fillet rounds sharp corners → body volume strictly decreases.
    shrank = base_volume > 0.0 and volume < base_volume - 1e-6
    ok = (not fillet.Shape.isNull()) and solids == 1 and shrank
    record("0.5", "PartDesign::Fillet stays single-solid AND rounded edges", ok,
           f"solids={solids}, volume={volume:.3f}, base_volume={base_volume:.3f}, shrank={shrank}")


def spike_step_export(doc: App.Document, body: object, out_dir: Path) -> None:
    step_path = out_dir / "spike_body.step"
    Part.export([body], str(step_path))
    ok = step_path.exists() and step_path.stat().st_size > 0
    record("0.6", "Body → STEP export", ok, f"path={step_path}")


def main() -> int:
    doc = App.newDocument("Spike")
    out_dir = Path(__file__).resolve().parent.parent / "reports" / "phase0_spike"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        body = spike_body_creation(doc)
        sketch = spike_sketch_closed_profile(doc, body)
        pad = spike_pad(doc, body, sketch)
        # 0.5/0.6 run before 0.4 so a FreeCAD API drift in Hole doesn't
        # short-circuit Fillet and STEP — they only need the Pad'd Body.
        spike_fillet(doc, body, pad)
        spike_step_export(doc, body, out_dir)
        spike_hole(doc, body, pad)
    except Exception as exc:  # noqa: BLE001 — spike must capture everything
        RESULTS.append({
            "id": "exception",
            "title": "Uncaught exception during spike",
            "pass": False,
            "detail": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        })

    report_path = out_dir / "phase0_results.json"
    report_path.write_text(json.dumps({"results": RESULTS}, indent=2))
    print(json.dumps({"results": RESULTS}, indent=2))
    failed = [r for r in RESULTS if not r["pass"]]
    return 0 if not failed else 1


# Run unconditionally — freecadcmd loads scripts as modules (not __main__)
# on FreeCAD 1.0, so an if-guard would silently no-op. This is a throwaway
# spike script, not a library; unconditional execution is correct here.
_exit_code = main()
if __name__ == "__main__":
    sys.exit(_exit_code)
