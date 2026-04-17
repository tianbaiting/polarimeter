# Detector Clamp Weldment Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the DPOL polarimeter detector-clamp fixture (Sub-2 of a 6-step manufacturability roadmap) so each detector position emits three named single-solid PartDesign Bodies — `Weldment_LoadBearing`, `UpperClamp_Detachable`, `BasePlate_Bolted` — plus real fastener solids, with no intentional interpenetration and a new strict validator guarding that property.

**Architecture:** Approach Y (PartDesign API) from the spec. Each Body is a `PartDesign::Body` with a feature tree of Sketches/Pads/Holes/Fillets/Chamfers. Adjacent Pads share coplanar mating faces (no 1 mm fuse-bite). Fasteners are simplified `Part` primitive solids for speed. BLP_v1 topology is preserved. Phase 0 is a headless feasibility spike that gates all later phases; on failure, fall back locally to Approach X (Part primitives + OCC fillets) with documented carve-outs.

**Tech Stack:** Python 3, FreeCAD (PartDesign, Part, Sketcher workbench APIs, `freecadcmd` headless), pytest, existing `ifsm` source tree under `infrontofSamuraiMag/src/ifsm/`.

**Spec:** `docs/superpowers/specs/2026-04-17-detector-clamp-weldment-redesign-design.md`

---

## Ground Rules for the Executor

- Every task below is TDD: write failing test → run it red → implement → run it green → commit.
- Tests that require FreeCAD get `pytestmark = pytest.mark.freecad_runtime` (already skipped by `conftest.py` when FreeCAD is absent). Pure-Python tests get `pytest.mark.pure_python`.
- Work inside the venv: `infrontofSamuraiMag/.venv-pytest/bin/python`.
- Test entry: `infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q infrontofSamuraiMag/tests`.
- After each implementation task, also run the strict-validate smoke commands from the regression phase (Task 14) locally if the change touches `components.py` / `validation.py`.
- Do **not** change `detector_fixture_geometry()` — the 12 placement positions are frozen for this plan.
- Do **not** remove or edit `skip_overlap_checks` or existing whitelist-overlap call sites elsewhere in `components.py`. Sub-1 (separate plan) owns that cleanup.

---

## Phase 0 — Headless PartDesign Feasibility (gates everything)

### Task 1: Write the Phase 0 spike script

**Files:**
- Create: `infrontofSamuraiMag/scripts/spike_partdesign_headless.py`

- [ ] **Step 1: Create the script**

```python
# infrontofSamuraiMag/scripts/spike_partdesign_headless.py
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
    sketch.Support = (doc.getObject("XY_Plane"), [""]) if doc.getObject("XY_Plane") else None
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
    ok = (not pad.Shape.isNull()) and len(body.Shape.Solids) == 1
    record("0.3", "PartDesign::Pad gives single-solid Body", ok,
           f"solids={len(body.Shape.Solids)}")
    return pad


def spike_hole(doc: App.Document, body: object) -> None:
    hole_sketch = body.newObject("Sketcher::SketchObject", "SpikeHoleSketch")
    hole_sketch.addGeometry(Part.Circle(App.Vector(10, 5, 10), App.Vector(0, 0, 1), 1.5), False)
    doc.recompute()
    hole = body.newObject("PartDesign::Hole", "SpikeHole")
    hole.Profile = hole_sketch
    hole.ThreadType = "ISOMetricProfile"
    hole.ThreadSize = "M3"
    hole.Depth = "Dimension"
    hole.DepthValue = 5.0
    doc.recompute()
    ok = hasattr(hole, "ThreadSize") and hole.ThreadSize == "M3" and not hole.Shape.isNull()
    record("0.4", "PartDesign::Hole ISO threaded", ok,
           f"ThreadSize={getattr(hole, 'ThreadSize', None)}")


def spike_fillet(doc: App.Document, body: object) -> None:
    edges = body.Shape.Edges
    # Pick any non-degenerate edge; spike only verifies the API doesn't null-face.
    edge_names = [f"Edge{i+1}" for i in range(min(2, len(edges)))]
    fillet = body.newObject("PartDesign::Fillet", "SpikeFillet")
    fillet.Base = (body.Shape, edge_names) if hasattr(fillet, "Base") else None
    if hasattr(fillet, "Radius"):
        fillet.Radius = 1.0
    doc.recompute()
    ok = (not fillet.Shape.isNull()) and len(body.Shape.Solids) == 1
    record("0.5", "PartDesign::Fillet stays single-solid", ok,
           f"solids={len(body.Shape.Solids)}")


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
        spike_pad(doc, body, sketch)
        spike_hole(doc, body)
        spike_fillet(doc, body)
        spike_step_export(doc, body, out_dir)
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


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the spike**

Run:
```bash
freecadcmd infrontofSamuraiMag/scripts/spike_partdesign_headless.py
```

Expected: JSON report printed; exit 0 if all 6 pass, exit 1 otherwise. Report also saved to `infrontofSamuraiMag/reports/phase0_spike/phase0_results.json`.

- [ ] **Step 3: Commit**

```bash
git add infrontofSamuraiMag/scripts/spike_partdesign_headless.py
git commit -m "Add Phase 0 PartDesign headless feasibility spike script"
```

---

### Task 2: Write Phase 0 outcome report + go/no-go

**Files:**
- Create: `docs/superpowers/specs/2026-04-17-phase0-partdesign-spike-report.md`
- Modify: `infrontofSamuraiMag/worklog.md` (append entry)
- Modify: `worklog.md` (append entry)

- [ ] **Step 1: Write report from spike JSON**

Template (fill in from `phase0_results.json`):

```markdown
# Phase 0 — Headless PartDesign Feasibility Report

- **Date**: 2026-04-17 (adjust on run)
- **Spike script**: `infrontofSamuraiMag/scripts/spike_partdesign_headless.py`
- **Raw output**: `infrontofSamuraiMag/reports/phase0_spike/phase0_results.json`
- **FreeCAD version**: <fill in: `freecadcmd --version`>

## Results

| # | Capability | Status | Detail |
|---|---|---|---|
| 0.1 | PartDesign::Body creation | pass/fail | ... |
| 0.2 | Sketcher closed profile | pass/fail | ... |
| 0.3 | Pad → single-solid Body | pass/fail | ... |
| 0.4 | Hole with ISO threading | pass/fail | ... |
| 0.5 | Fillet on Body edge | pass/fail | ... |
| 0.6 | Body → STEP export | pass/fail | ... |

## Decision

- **If all pass**: proceed with Approach Y as planned (Tasks 3–15).
- **If 0.1 or 0.2 or 0.3 or 0.6 fail**: STOP. Re-open spec. Do not proceed to Task 3.
- **If 0.4 fails (Hole)**: carve-out — replace `PartDesign::Hole` with `PartDesign::Pocket` fed by a circular sketch; BOM text records the thread spec instead of the feature.
- **If 0.5 fails (Fillet)**: carve-out — emit Bodies without fillets, add Part-level `shape.makeFillet(r, edges)` after Body finalization. Accept OCC fragility risk; record test flakes if they surface.

## Carve-outs (fill in per actual results)

- ...

## Next

- Proceed to Task 3 if decision allows.
```

- [ ] **Step 2: Append worklog entries**

Append to `infrontofSamuraiMag/worklog.md`:

```
- Timestamp UTC: <fill in>
- Timestamp Local: <fill in>
- Module/Scope: Sub-2 Phase 0 — headless PartDesign feasibility
- Command(s): `freecadcmd infrontofSamuraiMag/scripts/spike_partdesign_headless.py`
- Key Parameters/Overrides: spike script at HEAD; six capabilities 0.1–0.6
- Validation Result: <pass|partial|fail>
- Artifacts/State: `infrontofSamuraiMag/reports/phase0_spike/phase0_results.json`; report at `docs/superpowers/specs/2026-04-17-phase0-partdesign-spike-report.md`
- Next Action: <per Decision section>
```

Append same format to `polarimeter/worklog.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-17-phase0-partdesign-spike-report.md \
        infrontofSamuraiMag/worklog.md \
        worklog.md \
        infrontofSamuraiMag/reports/phase0_spike/
git commit -m "Phase 0 PartDesign feasibility report and worklog entries"
```

- [ ] **Step 4: Gate check**

If the report's Decision says **STOP**, do not continue. Return to the spec. Otherwise continue to Task 3.

---

## Phase 1 — Foundations (config + helpers)

### Task 3: Extend `DetectorClampConfig` with four new fields

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/config.py:177-201`
- Test: `infrontofSamuraiMag/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Append to `infrontofSamuraiMag/tests/test_config.py`:

```python
def test_clamp_config_has_new_manufacturing_fields() -> None:
    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    clamp = cfg.geometry.detector.clamp
    assert clamp.fillet_radius_mm == pytest.approx(3.0)
    assert clamp.chamfer_mm == pytest.approx(1.0)
    assert clamp.bolt_head_type == "ISO4762_hex_socket"
    assert clamp.draw_fasteners_as_solids is True


def test_clamp_config_backward_compat_defaults_when_absent(tmp_path) -> None:
    """Old configs without the new fields still load, with defaults applied."""
    import yaml
    src = ROOT / "config" / "default_infront.yaml"
    data = yaml.safe_load(src.read_text())
    clamp = data["geometry"]["detector"]["clamp"]
    for key in ("fillet_radius_mm", "chamfer_mm", "bolt_head_type", "draw_fasteners_as_solids"):
        clamp.pop(key, None)
    legacy_path = tmp_path / "legacy.yaml"
    legacy_path.write_text(yaml.safe_dump(data))
    cfg = load_build_config(legacy_path)
    assert cfg.geometry.detector.clamp.fillet_radius_mm == pytest.approx(3.0)
    assert cfg.geometry.detector.clamp.chamfer_mm == pytest.approx(1.0)
    assert cfg.geometry.detector.clamp.bolt_head_type == "ISO4762_hex_socket"
    assert cfg.geometry.detector.clamp.draw_fasteners_as_solids is True
```

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_config.py::test_clamp_config_has_new_manufacturing_fields
```

Expected: FAIL with `AttributeError: 'DetectorClampConfig' object has no attribute 'fillet_radius_mm'`.

- [ ] **Step 3: Implement — add fields to dataclass**

In `infrontofSamuraiMag/src/ifsm/config.py`, locate `DetectorClampConfig` (around line 177). Append these four fields at the end of the class body (keeping frozen=True):

```python
    fillet_radius_mm: float = 3.0
    chamfer_mm: float = 1.0
    bolt_head_type: str = "ISO4762_hex_socket"
    draw_fasteners_as_solids: bool = True
```

If the existing dataclass has no default-valued fields, Python's `@dataclass(frozen=True)` requires all defaulted fields to come after non-defaulted ones — that's already satisfied here since we're appending.

- [ ] **Step 4: Wire the YAML loader**

Find the clamp loader (search for `DetectorClampConfig(` in `config.py`). Add the four field reads from the YAML dict, each with `.get(...)` defaulting to the dataclass default:

```python
    # Inside the function that constructs DetectorClampConfig from a dict 'clamp':
    fillet_radius_mm=float(clamp.get("fillet_radius_mm", 3.0)),
    chamfer_mm=float(clamp.get("chamfer_mm", 1.0)),
    bolt_head_type=str(clamp.get("bolt_head_type", "ISO4762_hex_socket")),
    draw_fasteners_as_solids=bool(clamp.get("draw_fasteners_as_solids", True)),
```

- [ ] **Step 5: Run both tests, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_config.py::test_clamp_config_has_new_manufacturing_fields \
  infrontofSamuraiMag/tests/test_config.py::test_clamp_config_backward_compat_defaults_when_absent
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/config.py infrontofSamuraiMag/tests/test_config.py
git commit -m "Add fillet/chamfer/bolt_head_type/draw_fasteners_as_solids to DetectorClampConfig"
```

---

### Task 4: Guard against unsafe `fillet_radius_mm`

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/config.py` (clamp loader function)
- Test: `infrontofSamuraiMag/tests/test_config.py`

- [ ] **Step 1: Write failing test**

Append:

```python
def test_clamp_fillet_radius_guard_rejects_too_large(tmp_path) -> None:
    import yaml
    src = ROOT / "config" / "default_infront.yaml"
    data = yaml.safe_load(src.read_text())
    data["geometry"]["detector"]["clamp"]["fillet_radius_mm"] = 999.0
    bad_path = tmp_path / "bad_fillet.yaml"
    bad_path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="fillet_radius_mm"):
        load_build_config(bad_path)
```

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_config.py::test_clamp_fillet_radius_guard_rejects_too_large
```

Expected: FAIL (no exception raised).

- [ ] **Step 3: Add the guard**

In the same clamp loader function in `config.py`, immediately after `DetectorClampConfig(...)` is built, compute a minimum adjacent face span and validate. Insert before returning:

```python
    # Guard: fillet_radius_mm must be ≤ half of the smallest adjacent face span
    # among saddle/adapter/upright/bridge interfaces. Uses the narrowest of the
    # relevant pad widths as a conservative proxy.
    adapter = clamp_cfg_container.get("adapter_block", {})
    min_span = min(
        float(adapter.get("width_mm", 1.0)),
        float(adapter.get("height_mm", 1.0)),
        float(clamp.get("width_mm", 1.0)),
    )
    if clamp_obj.fillet_radius_mm > 0.5 * min_span:
        raise ValueError(
            f"fillet_radius_mm={clamp_obj.fillet_radius_mm:.3f} exceeds half of "
            f"the narrowest adjacent span={min_span:.3f} mm; reduce the radius "
            f"or widen saddle/adapter/clamp widths."
        )
```

(Adjust `clamp_cfg_container` / `clamp_obj` to match the local variable names in the loader.)

- [ ] **Step 4: Run, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_config.py::test_clamp_fillet_radius_guard_rejects_too_large
```

Expected: PASS. Also re-run prior tests from Task 3 to confirm no regression.

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/config.py infrontofSamuraiMag/tests/test_config.py
git commit -m "Guard DetectorClampConfig.fillet_radius_mm against excessive values"
```

---

### Task 5: Create `primitives_fasteners.py` module

**Files:**
- Create: `infrontofSamuraiMag/src/ifsm/primitives_fasteners.py`
- Create: `infrontofSamuraiMag/tests/test_primitives_fasteners.py`

- [ ] **Step 1: Write failing test**

```python
# infrontofSamuraiMag/tests/test_primitives_fasteners.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def test_hex_socket_bolt_is_single_solid() -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_hex_socket_bolt

    shape = make_hex_socket_bolt(
        size="M6",
        shank_length_mm=25.0,
        origin=App.Vector(0, 0, 0),
        axis=App.Vector(0, 0, 1),
    )
    assert len(shape.Solids) == 1
    assert shape.Volume > 0.0


def test_hex_nut_is_single_solid() -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_hex_nut

    shape = make_hex_nut(
        size="M6",
        origin=App.Vector(0, 0, 0),
        axis=App.Vector(0, 0, 1),
    )
    assert len(shape.Solids) == 1
    assert shape.Volume > 0.0


def test_flat_washer_is_single_solid() -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_flat_washer

    shape = make_flat_washer(
        size="M6",
        origin=App.Vector(0, 0, 0),
        axis=App.Vector(0, 0, 1),
    )
    assert len(shape.Solids) == 1
    assert shape.Volume > 0.0


def test_unknown_size_raises() -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_hex_socket_bolt

    with pytest.raises(KeyError):
        make_hex_socket_bolt("M99", 10.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
```

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_primitives_fasteners.py -m freecad_runtime
```

Expected: FAIL (ModuleNotFoundError or import error).

- [ ] **Step 3: Implement the module**

```python
# infrontofSamuraiMag/src/ifsm/primitives_fasteners.py
"""Simplified fastener solids for review-quality visual mockup.

These are NOT drawing-class: nut chamfers and thread detail are intentionally
omitted. Use for visualizing bolt placement; BOM text carries the ISO spec.
"""
from __future__ import annotations

import math

import FreeCAD as App
import Part


# ISO-ish proportions; keys are the thread sizes we support.
# shank_diameter / head_diameter / head_height / wrench_across_flats (nut) / washer_outer / washer_inner
_BOLT_TABLE: dict[str, dict[str, float]] = {
    "M3": {"shank_d": 3.0, "head_d": 5.5, "head_h": 3.0, "nut_afs": 5.5, "washer_od": 7.0, "washer_id": 3.2, "washer_t": 0.5},
    "M4": {"shank_d": 4.0, "head_d": 7.0, "head_h": 4.0, "nut_afs": 7.0, "washer_od": 9.0, "washer_id": 4.3, "washer_t": 0.8},
    "M5": {"shank_d": 5.0, "head_d": 8.5, "head_h": 5.0, "nut_afs": 8.0, "washer_od": 10.0, "washer_id": 5.3, "washer_t": 1.0},
    "M6": {"shank_d": 6.0, "head_d": 10.0, "head_h": 6.0, "nut_afs": 10.0, "washer_od": 12.0, "washer_id": 6.4, "washer_t": 1.6},
    "M8": {"shank_d": 8.0, "head_d": 13.0, "head_h": 8.0, "nut_afs": 13.0, "washer_od": 16.0, "washer_id": 8.4, "washer_t": 1.6},
    "M10": {"shank_d": 10.0, "head_d": 16.0, "head_h": 10.0, "nut_afs": 17.0, "washer_od": 20.0, "washer_id": 10.5, "washer_t": 2.0},
}


def _lookup(size: str) -> dict[str, float]:
    if size not in _BOLT_TABLE:
        raise KeyError(f"Unsupported fastener size: {size!r}. Known: {sorted(_BOLT_TABLE)}")
    return _BOLT_TABLE[size]


def _hex_prism(center: App.Vector, axis: App.Vector, afs: float, height: float) -> Part.Shape:
    """A hex prism; 'afs' is wrench across flats."""
    # Build on XY plane then rotate so axis aligns with 'axis'.
    radius_across_corners = afs / math.sqrt(3.0)
    vertices = []
    for i in range(6):
        theta = math.radians(30.0 + 60.0 * i)
        vertices.append(App.Vector(radius_across_corners * math.cos(theta),
                                   radius_across_corners * math.sin(theta),
                                   0.0))
    vertices.append(vertices[0])
    wire = Part.makePolygon(vertices)
    face = Part.Face(wire)
    prism = face.extrude(App.Vector(0, 0, height))
    # Rotate to target axis
    rot = App.Rotation(App.Vector(0, 0, 1), axis)
    prism.Placement = App.Placement(App.Vector(0, 0, 0), rot)
    prism.translate(center)
    return prism


def make_hex_socket_bolt(
    size: str,
    shank_length_mm: float,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    """Origin is the under-head seat face center; axis points from head toward tip."""
    spec = _lookup(size)
    axis = App.Vector(axis).normalize()
    head_origin = origin - axis.multiply(spec["head_h"])
    head = Part.makeCylinder(0.5 * spec["head_d"], spec["head_h"], head_origin, axis)
    shank = Part.makeCylinder(0.5 * spec["shank_d"], shank_length_mm, origin, axis)
    return head.fuse(shank)


def make_hex_nut(
    size: str,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    """Origin is the seat face center; axis perpendicular to the nut face."""
    spec = _lookup(size)
    nut_height = 0.8 * spec["shank_d"]
    outer = _hex_prism(App.Vector(origin), App.Vector(axis), spec["nut_afs"], nut_height)
    bore = Part.makeCylinder(
        0.5 * spec["shank_d"],
        nut_height + 0.4,
        App.Vector(origin) - App.Vector(axis).multiply(0.2),
        App.Vector(axis),
    )
    return outer.cut(bore)


def make_flat_washer(
    size: str,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    spec = _lookup(size)
    outer = Part.makeCylinder(0.5 * spec["washer_od"], spec["washer_t"], origin, axis)
    bore = Part.makeCylinder(
        0.5 * spec["washer_id"],
        spec["washer_t"] + 0.4,
        App.Vector(origin) - App.Vector(axis).normalize().multiply(0.2),
        axis,
    )
    return outer.cut(bore)
```

- [ ] **Step 4: Run, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_primitives_fasteners.py
```

Expected: PASS (or SKIP if FreeCAD unavailable — then run under `freecadcmd` to validate separately).

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/primitives_fasteners.py \
        infrontofSamuraiMag/tests/test_primitives_fasteners.py
git commit -m "Add primitives_fasteners module (hex-socket bolt, hex nut, flat washer)"
```

---

### Task 6: Add PartDesign helpers to `primitives.py`

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/primitives.py` (append)
- Create: `infrontofSamuraiMag/tests/test_primitives_partdesign.py`

- [ ] **Step 1: Write failing tests**

```python
# infrontofSamuraiMag/tests/test_primitives_partdesign.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def test_new_body_returns_fresh_body() -> None:
    import FreeCAD as App
    from ifsm.primitives import new_partdesign_body

    doc = App.newDocument("TestDoc")
    body = new_partdesign_body(doc, "TestBody")
    assert body.TypeId == "PartDesign::Body"
    assert body.Name == "TestBody"


def test_pad_rectangle_profile_produces_single_solid() -> None:
    import FreeCAD as App
    from ifsm.primitives import new_partdesign_body, pad_rectangle

    doc = App.newDocument("TestPad")
    body = new_partdesign_body(doc, "B")
    pad_rectangle(
        body,
        origin=App.Vector(0, 0, 0),
        axis_u=App.Vector(1, 0, 0),
        axis_v=App.Vector(0, 1, 0),
        axis_w=App.Vector(0, 0, 1),
        width_mm=20.0,
        height_mm=10.0,
        pad_length_mm=5.0,
        name="PadRect",
    )
    doc.recompute()
    assert len(body.Shape.Solids) == 1


def test_select_edges_by_predicate_finds_convex_edges() -> None:
    import FreeCAD as App
    from ifsm.primitives import new_partdesign_body, pad_rectangle, select_edges_by_predicate

    doc = App.newDocument("TestEdges")
    body = new_partdesign_body(doc, "B")
    pad_rectangle(body, App.Vector(0, 0, 0),
                  App.Vector(1, 0, 0), App.Vector(0, 1, 0), App.Vector(0, 0, 1),
                  20.0, 10.0, 5.0, "PadRect")
    doc.recompute()
    edges = select_edges_by_predicate(body, lambda e: True)
    assert len(edges) > 0
    # All names must match the form 'Edge<N>'
    for name in edges:
        assert name.startswith("Edge")
```

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_primitives_partdesign.py
```

Expected: FAIL (ImportError — new helpers don't exist).

- [ ] **Step 3: Append helpers to `primitives.py`**

Append to `infrontofSamuraiMag/src/ifsm/primitives.py`:

```python
# --- PartDesign helpers (added for Sub-2 detector clamp weldment redesign) ---

import Sketcher  # type: ignore  # noqa: E402


def new_partdesign_body(doc: App.Document, name: str):
    """Create a PartDesign::Body attached to the active document."""
    return doc.addObject("PartDesign::Body", name)


def pad_rectangle(
    body,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_w: App.Vector,
    width_mm: float,
    height_mm: float,
    pad_length_mm: float,
    name: str,
):
    """Sketch an axis-aligned rectangle on the (u,v) plane at origin, pad along axis_w.

    `axis_u` is the rectangle's width direction, `axis_v` is height. The sketch
    support is an auxiliary Plane on the body's origin; the sketch geometry is
    transformed to world via the Placement after recompute. For the feature
    tree this still produces a single Pad of the Body.
    """
    sketch = body.newObject("Sketcher::SketchObject", f"Sketch_{name}")
    # Place the sketch plane so u/v match world (u,v) at origin.
    placement = App.Placement()
    placement.Base = App.Vector(origin)
    rot = App.Rotation(App.Vector(0, 0, 1), App.Vector(axis_w))
    placement.Rotation = rot
    sketch.Placement = placement
    half_w = 0.5 * width_mm
    half_h = 0.5 * height_mm
    p1 = App.Vector(-half_w, -half_h, 0)
    p2 = App.Vector(half_w, -half_h, 0)
    p3 = App.Vector(half_w, half_h, 0)
    p4 = App.Vector(-half_w, half_h, 0)
    sketch.addGeometry(Part.LineSegment(p1, p2), False)
    sketch.addGeometry(Part.LineSegment(p2, p3), False)
    sketch.addGeometry(Part.LineSegment(p3, p4), False)
    sketch.addGeometry(Part.LineSegment(p4, p1), False)
    for i in range(4):
        sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    pad = body.newObject("PartDesign::Pad", f"Pad_{name}")
    pad.Profile = sketch
    pad.Length = pad_length_mm
    pad.Midplane = True  # symmetric pad about sketch plane
    body.Document.recompute()
    return pad


def pad_half_annulus(
    body,
    origin: App.Vector,
    axis_u: App.Vector,  # along the cylinder's length (pad direction)
    axis_v: App.Vector,  # split-plane normal (which half)
    axis_w: App.Vector,  # in-split-plane perpendicular
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    pad_length_mm: float,
    name: str,
):
    """Sketch a half-annulus on the (v,w) plane at origin, pad along axis_u.

    The half is the `+w` side of the split plane.
    """
    sketch = body.newObject("Sketcher::SketchObject", f"Sketch_{name}")
    placement = App.Placement()
    placement.Base = App.Vector(origin)
    rot = App.Rotation(App.Vector(0, 0, 1), App.Vector(axis_u))
    placement.Rotation = rot
    sketch.Placement = placement
    ro = 0.5 * outer_diameter_mm
    ri = 0.5 * inner_diameter_mm
    # Outer arc: left half (w>0 only). Start at (-ro, 0) mid (0, ro) end (ro, 0)
    outer_arc = Part.ArcOfCircle(
        Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ro),
        0.0,
        math.pi,
    )
    inner_arc = Part.ArcOfCircle(
        Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ri),
        0.0,
        math.pi,
    )
    left_seg = Part.LineSegment(App.Vector(-ro, 0, 0), App.Vector(-ri, 0, 0))
    right_seg = Part.LineSegment(App.Vector(ri, 0, 0), App.Vector(ro, 0, 0))
    sketch.addGeometry(outer_arc, False)
    sketch.addGeometry(left_seg, False)
    sketch.addGeometry(inner_arc, False)
    sketch.addGeometry(right_seg, False)
    # Coincidence constraints to close the wire
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 1, 1, 1))  # outer start ↔ left seg start
    sketch.addConstraint(Sketcher.Constraint("Coincident", 1, 2, 2, 2))  # left seg end ↔ inner end
    sketch.addConstraint(Sketcher.Constraint("Coincident", 2, 1, 3, 1))  # inner start ↔ right seg start
    sketch.addConstraint(Sketcher.Constraint("Coincident", 3, 2, 0, 2))  # right seg end ↔ outer end
    pad = body.newObject("PartDesign::Pad", f"Pad_{name}")
    pad.Profile = sketch
    pad.Length = pad_length_mm
    pad.Midplane = True
    body.Document.recompute()
    return pad


def add_fillet(body, radius_mm: float, edge_names: list[str], name: str):
    """Add PartDesign::Fillet on specified edges of the body."""
    fillet = body.newObject("PartDesign::Fillet", f"Fillet_{name}")
    fillet.Base = (body, edge_names)
    fillet.Radius = radius_mm
    body.Document.recompute()
    return fillet


def add_chamfer(body, size_mm: float, edge_names: list[str], name: str):
    chamfer = body.newObject("PartDesign::Chamfer", f"Chamfer_{name}")
    chamfer.Base = (body, edge_names)
    chamfer.Size = size_mm
    body.Document.recompute()
    return chamfer


def add_hole(
    body,
    center: App.Vector,
    axis: App.Vector,
    thread_size: str,
    depth_mm: float,
    name: str,
):
    """Add an ISO threaded hole on the body. Profile is a single circle in a sketch."""
    sketch = body.newObject("Sketcher::SketchObject", f"Sketch_{name}")
    placement = App.Placement()
    placement.Base = App.Vector(center)
    rot = App.Rotation(App.Vector(0, 0, 1), App.Vector(axis))
    placement.Rotation = rot
    sketch.Placement = placement
    clearance_d = {"M3": 3.4, "M4": 4.5, "M5": 5.5, "M6": 6.6, "M8": 9.0, "M10": 11.0}[thread_size]
    sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 0.5 * clearance_d), False)
    hole = body.newObject("PartDesign::Hole", f"Hole_{name}")
    hole.Profile = sketch
    hole.ThreadType = "ISOMetricProfile"
    hole.ThreadSize = thread_size
    hole.Depth = "Dimension"
    hole.DepthValue = depth_mm
    body.Document.recompute()
    return hole


def select_edges_by_predicate(body, predicate) -> list[str]:
    """Return edge names ('Edge1', 'Edge2', ...) passing the predicate on the edge shape."""
    names: list[str] = []
    for idx, edge in enumerate(body.Shape.Edges, start=1):
        if predicate(edge):
            names.append(f"Edge{idx}")
    return names
```

Also ensure `import math` is present at the top of `primitives.py`.

- [ ] **Step 4: Run, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_primitives_partdesign.py
```

Expected: PASS (or SKIP without FreeCAD — run under `freecadcmd`).

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/primitives.py \
        infrontofSamuraiMag/tests/test_primitives_partdesign.py
git commit -m "Add PartDesign helpers (body, pads, fillet/chamfer, hole, edge selector)"
```

---

## Phase 2 — Three Bodies

### Task 7: Build `Weldment_LoadBearing` Body

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/components.py` (add new function, do NOT delete old `build_detector_fixture` yet)
- Create: `infrontofSamuraiMag/tests/test_weldment_body.py`

- [ ] **Step 1: Write failing test**

```python
# infrontofSamuraiMag/tests/test_weldment_body.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def _load_cfg_and_placement():
    import FreeCAD as App  # noqa: F401
    from ifsm.config import load_build_config
    from ifsm.layout import compute_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = compute_detector_placements(cfg.geometry)
    return cfg.geometry, placements[0]


def test_weldment_is_single_solid_for_first_placement() -> None:
    import FreeCAD as App
    from ifsm.components import build_weldment_load_bearing

    geom, placement = _load_cfg_and_placement()
    doc = App.newDocument("TestWeldment")
    body = build_weldment_load_bearing(doc, geom, placement)
    assert len(body.Shape.Solids) == 1


def test_weldment_has_fillets_and_chamfers() -> None:
    import FreeCAD as App
    from ifsm.components import build_weldment_load_bearing

    geom, placement = _load_cfg_and_placement()
    doc = App.newDocument("TestWeldment2")
    body = build_weldment_load_bearing(doc, geom, placement)
    types = [obj.TypeId for obj in body.Group]
    assert types.count("PartDesign::Fillet") >= 2
    assert types.count("PartDesign::Chamfer") >= 1


def test_weldment_all_12_placements_build() -> None:
    import FreeCAD as App
    from ifsm.components import build_weldment_load_bearing
    from ifsm.config import load_build_config
    from ifsm.layout import compute_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = compute_detector_placements(cfg.geometry)
    assert len(placements) == 12
    doc = App.newDocument("TestWeldment12")
    for i, p in enumerate(placements):
        body = build_weldment_load_bearing(doc, cfg.geometry, p, name_suffix=f"_{i}")
        assert len(body.Shape.Solids) == 1, f"placement {i} ({p.tag}) produced {len(body.Shape.Solids)} solids"
```

(If the existing module function for placements has a different name — check `infrontofSamuraiMag/src/ifsm/layout.py` or `components.py` — substitute the correct import.)

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_weldment_body.py
```

Expected: FAIL (ImportError, `build_weldment_load_bearing` missing).

- [ ] **Step 3: Implement `build_weldment_load_bearing`**

In `infrontofSamuraiMag/src/ifsm/components.py`, near the bottom (do not delete `build_detector_fixture` yet), add:

```python
from .primitives import (  # noqa: E402  add near existing primitives imports
    new_partdesign_body,
    pad_rectangle,
    pad_half_annulus,
    add_fillet,
    add_chamfer,
    add_hole,
    select_edges_by_predicate,
)


def build_weldment_load_bearing(
    doc,
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    name_suffix: str = "",
):
    """Build the load-bearing weldment as a single PartDesign::Body.

    Contents (BLP_v1 topology, single solid after recompute):
      - lower half-annulus clamp ring (with anti-rotation key rib on bore)
      - lower saddle pad (under ring, transitioning to the adapter block)
      - adapter/transition block pad
      - twin uprights pad
      - top bridge pad
      - threaded holes for the uprights-to-bridge connection (if any)
      - fillets at saddle↔ring, adapter↔saddle, uprights↔bridge interfaces
      - chamfer on external edges
    """
    clamp_cfg = cfg.detector.clamp
    adapter_cfg = cfg.detector.adapter_block
    layout = detector_fixture_geometry(cfg, placement)

    body_name = f"Weldment_LoadBearing_{placement.tag}{name_suffix}"
    body = new_partdesign_body(doc, body_name)

    # 1) Lower half-annulus clamp ring — half whose saddle side is 'support_saddle_center' side.
    support_direction = (layout.support_saddle_center - layout.clamp_center)
    if support_direction.Length > 1e-9:
        support_direction = support_direction.normalize()
    else:
        support_direction = layout.mount_axis  # fallback
    pad_half_annulus(
        body,
        origin=layout.clamp_center,
        axis_u=layout.direction,           # pad direction = along detector axis
        axis_v=support_direction,          # normal to split plane, pointing toward saddle
        axis_w=layout.clamp_bolt_axis,     # in the split plane
        outer_diameter_mm=clamp_cfg.outer_diameter_mm,
        inner_diameter_mm=clamp_cfg.inner_diameter_mm,
        pad_length_mm=clamp_cfg.width_mm,
        name="HalfRing",
    )

    # 2) Lower saddle pad
    pad_rectangle(
        body,
        origin=layout.support_saddle_center,
        axis_u=layout.direction,
        axis_v=support_direction,
        axis_w=layout.mount_lateral_axis,
        width_mm=layout.support_saddle_length_mm,
        height_mm=layout.support_saddle_height_mm,
        pad_length_mm=layout.support_saddle_thickness_mm,
        name="Saddle",
    )

    # 3) Adapter (transition) block pad
    pad_rectangle(
        body,
        origin=layout.block_center,
        axis_u=layout.direction,
        axis_v=layout.mount_axis,
        axis_w=layout.mount_lateral_axis,
        width_mm=adapter_cfg.length_mm,
        height_mm=adapter_cfg.height_mm,
        pad_length_mm=adapter_cfg.width_mm,
        name="AdapterBlock",
    )

    # 4) Twin uprights (one pad with two-island profile is complex; use two pads)
    for idx, offset in enumerate(layout.upright_offsets, start=1):
        upright_center = layout.bridge_plate_face_center - offset_vector(
            layout.direction, offset
        )  # helper below or inline; see adjusted impl notes
        pad_rectangle(
            body,
            origin=upright_center,
            axis_u=layout.direction,
            axis_v=layout.mount_axis,
            axis_w=layout.mount_lateral_axis,
            width_mm=layout.upright_width_mm,
            height_mm=layout.upright_depth_mm,
            pad_length_mm=layout.upright_length_mm,
            name=f"Upright{idx}",
        )

    # 5) Top bridge
    pad_rectangle(
        body,
        origin=layout.bridge_center,
        axis_u=layout.direction,
        axis_v=layout.mount_axis,
        axis_w=layout.mount_lateral_axis,
        width_mm=layout.bridge_span_mm,
        height_mm=layout.bridge_depth_mm,
        pad_length_mm=layout.bridge_thickness_mm,
        name="Bridge",
    )

    # 6) Fillets: select convex edges on the saddle-to-ring junction, etc.
    # We pick edges by geometric predicate — "edges where both adjacent faces
    # contain the saddle_center in their bounding box and are perpendicular."
    all_edges = select_edges_by_predicate(body, lambda e: e.Length > 1.0)
    if all_edges:
        add_fillet(body, clamp_cfg.fillet_radius_mm, all_edges[: min(4, len(all_edges))], "SaddleToRing")
    outer_edges = select_edges_by_predicate(body, lambda e: e.Length > 2.0)
    if outer_edges:
        add_fillet(body, clamp_cfg.fillet_radius_mm, outer_edges[: min(2, len(outer_edges))], "UprightsToBridge")

    # 7) Chamfer external edges
    chamfer_edges = select_edges_by_predicate(body, lambda e: e.Length > 5.0)
    if chamfer_edges:
        add_chamfer(body, clamp_cfg.chamfer_mm, chamfer_edges[: min(4, len(chamfer_edges))], "ExternalEdges")

    doc.recompute()
    return body
```

Notes on the `offset_vector` usage: replace with existing helper `scaled(axis, value)` from `layout.py` if present; otherwise inline the scalar multiplication.

**The edge-selection predicates above are intentionally crude.** After Phase 0 passes, the executor should refine the `lambda` callbacks using the geometric properties that actually differentiate the intended edges (e.g., test whether the edge endpoints lie in the saddle-ring intersection plane). Keep the count-based `[:min(N, len(...))]` as a safety net so the feature never tries to fillet zero edges and fail.

- [ ] **Step 4: Run, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_weldment_body.py
```

Expected: PASS.

If Phase 0's Fillet item (0.5) carved out, replace `add_fillet` / `add_chamfer` calls with `shape.makeFillet` / `shape.makeChamfer` on the Body's `Shape` after pad recompute, and document the carve-out inline.

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/components.py infrontofSamuraiMag/tests/test_weldment_body.py
git commit -m "Add build_weldment_load_bearing (PartDesign single-solid Body)"
```

---

### Task 8: Build `UpperClamp_Detachable` Body

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/components.py`
- Create: `infrontofSamuraiMag/tests/test_upper_clamp_body.py`

- [ ] **Step 1: Write failing test**

```python
# infrontofSamuraiMag/tests/test_upper_clamp_body.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def test_upper_clamp_is_single_solid() -> None:
    import FreeCAD as App
    from ifsm.components import build_upper_clamp_detachable
    from ifsm.config import load_build_config
    from ifsm.layout import compute_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = compute_detector_placements(cfg.geometry)
    doc = App.newDocument("TestUpper")
    body = build_upper_clamp_detachable(doc, cfg.geometry, placements[0])
    assert len(body.Shape.Solids) == 1


def test_upper_clamp_has_chamfer() -> None:
    import FreeCAD as App
    from ifsm.components import build_upper_clamp_detachable
    from ifsm.config import load_build_config
    from ifsm.layout import compute_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = compute_detector_placements(cfg.geometry)
    doc = App.newDocument("TestUpperChamfer")
    body = build_upper_clamp_detachable(doc, cfg.geometry, placements[0])
    types = [obj.TypeId for obj in body.Group]
    assert types.count("PartDesign::Chamfer") >= 1
```

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_upper_clamp_body.py
```

Expected: FAIL (ImportError).

- [ ] **Step 3: Implement**

Append to `components.py`:

```python
def build_upper_clamp_detachable(
    doc,
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    name_suffix: str = "",
):
    """Upper half-clamp: half-annulus + ears (for clamp bolts)."""
    clamp_cfg = cfg.detector.clamp
    layout = detector_fixture_geometry(cfg, placement)
    body_name = f"UpperClamp_Detachable_{placement.tag}{name_suffix}"
    body = new_partdesign_body(doc, body_name)

    # Upper half (opposite side of saddle)
    support_direction = (layout.support_saddle_center - layout.clamp_center)
    support_direction = support_direction.normalize() if support_direction.Length > 1e-9 else layout.mount_axis
    upper_direction = App.Vector(-support_direction.x, -support_direction.y, -support_direction.z)
    pad_half_annulus(
        body,
        origin=layout.clamp_center,
        axis_u=layout.direction,
        axis_v=upper_direction,
        axis_w=layout.clamp_bolt_axis,
        outer_diameter_mm=clamp_cfg.outer_diameter_mm,
        inner_diameter_mm=clamp_cfg.inner_diameter_mm,
        pad_length_mm=clamp_cfg.width_mm,
        name="HalfRing",
    )

    # Ears with through-holes for clamp bolts. Two ears on each side.
    ear_offset = 0.5 * clamp_cfg.outer_diameter_mm + 0.5 * clamp_cfg.clamp_ear_thickness_mm - 0.5
    for side_sign in (-1.0, 1.0):
        ear_center = layout.clamp_center + scaled(layout.mount_lateral_axis, side_sign * ear_offset)
        pad_rectangle(
            body,
            origin=ear_center,
            axis_u=layout.direction,
            axis_v=upper_direction,
            axis_w=layout.mount_lateral_axis,
            width_mm=clamp_cfg.clamp_ear_length_mm,
            height_mm=clamp_cfg.clamp_ear_width_mm,
            pad_length_mm=clamp_cfg.clamp_ear_thickness_mm,
            name=f"Ear_{int(side_sign)}",
        )

    # Clamp bolt holes (through both ears; 2 ears × 2 bolt pitches)
    try:
        thread_size = _bolt_diameter_to_thread(clamp_cfg.clamp_bolt_diameter_mm)
    except KeyError:
        thread_size = "M6"  # safe default
    for side_sign in (-1.0, 1.0):
        for u_off in (-0.5 * clamp_cfg.clamp_bolt_pitch_mm, 0.5 * clamp_cfg.clamp_bolt_pitch_mm):
            hole_center = (
                layout.clamp_center
                + scaled(layout.direction, u_off)
                + scaled(layout.mount_lateral_axis, side_sign * ear_offset)
            )
            add_hole(body, hole_center, upper_direction, thread_size,
                     depth_mm=clamp_cfg.clamp_ear_thickness_mm + 0.4,
                     name=f"ClampBolt_{int(side_sign)}_{'p' if u_off > 0 else 'n'}")

    # External chamfer
    chamfer_edges = select_edges_by_predicate(body, lambda e: e.Length > 4.0)
    if chamfer_edges:
        add_chamfer(body, clamp_cfg.chamfer_mm, chamfer_edges[: min(4, len(chamfer_edges))], "ExternalEdges")

    doc.recompute()
    return body


def _bolt_diameter_to_thread(d_mm: float) -> str:
    tbl = {3.0: "M3", 4.0: "M4", 5.0: "M5", 6.0: "M6", 8.0: "M8", 10.0: "M10"}
    for key, val in tbl.items():
        if abs(key - d_mm) < 0.1:
            return val
    raise KeyError(f"No standard thread for diameter {d_mm} mm")
```

- [ ] **Step 4: Run, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_upper_clamp_body.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/components.py infrontofSamuraiMag/tests/test_upper_clamp_body.py
git commit -m "Add build_upper_clamp_detachable (PartDesign Body with ears and bolt holes)"
```

---

### Task 9: Build `BasePlate_Bolted` Body

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/components.py`
- Create: `infrontofSamuraiMag/tests/test_base_plate_body.py`

- [ ] **Step 1: Write failing test**

```python
# infrontofSamuraiMag/tests/test_base_plate_body.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def test_base_plate_is_single_solid() -> None:
    import FreeCAD as App
    from ifsm.components import build_base_plate_bolted
    from ifsm.config import load_build_config
    from ifsm.layout import compute_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = compute_detector_placements(cfg.geometry)
    doc = App.newDocument("TestBasePlate")
    body = build_base_plate_bolted(doc, cfg.geometry, placements[0])
    assert len(body.Shape.Solids) == 1


def test_base_plate_has_eight_holes() -> None:
    import FreeCAD as App
    from ifsm.components import build_base_plate_bolted
    from ifsm.config import load_build_config
    from ifsm.layout import compute_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = compute_detector_placements(cfg.geometry)
    doc = App.newDocument("TestBasePlateHoles")
    body = build_base_plate_bolted(doc, cfg.geometry, placements[0])
    types = [obj.TypeId for obj in body.Group]
    assert types.count("PartDesign::Hole") == 8  # 4 plate-side + 4 weldment-side
```

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_base_plate_body.py
```

Expected: FAIL (ImportError).

- [ ] **Step 3: Implement**

Append to `components.py`:

```python
def build_base_plate_bolted(
    doc,
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    name_suffix: str = "",
):
    """4-hole base plate: 4 plate-side through-holes + 4 weldment-side receiving holes."""
    clamp_cfg = cfg.detector.clamp
    layout = detector_fixture_geometry(cfg, placement)
    body_name = f"BasePlate_Bolted_{placement.tag}{name_suffix}"
    body = new_partdesign_body(doc, body_name)

    plate = layout.mount_base_top_center
    pad_rectangle(
        body,
        origin=plate,
        axis_u=layout.direction,
        axis_v=layout.mount_axis,
        axis_w=layout.mount_lateral_axis,
        width_mm=clamp_cfg.mount_base_u_mm,
        height_mm=clamp_cfg.mount_base_v_mm,
        pad_length_mm=clamp_cfg.mount_base_thickness_mm,
        name="Plate",
    )

    # Plate-side holes (to plate.h/v1/v2)
    try:
        plate_thread = _bolt_diameter_to_thread(clamp_cfg.mount_bolt_hole_diameter_mm)
    except KeyError:
        plate_thread = "M8"
    for idx, c in enumerate(layout.plate_hole_centers, start=1):
        add_hole(body, c, layout.mount_axis, plate_thread,
                 depth_mm=clamp_cfg.mount_base_thickness_mm + 0.4,
                 name=f"PlateSide_{idx}")

    # Weldment-side holes (receive the weldment's base bolts)
    for idx, c in enumerate(layout.base_hole_centers, start=1):
        add_hole(body, c, layout.mount_axis, plate_thread,
                 depth_mm=clamp_cfg.mount_base_thickness_mm + 0.4,
                 name=f"WeldmentSide_{idx}")

    chamfer_edges = select_edges_by_predicate(body, lambda e: e.Length > 5.0)
    if chamfer_edges:
        add_chamfer(body, clamp_cfg.chamfer_mm, chamfer_edges[: min(4, len(chamfer_edges))], "CornerEdges")

    doc.recompute()
    return body
```

- [ ] **Step 4: Run, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_base_plate_body.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/components.py infrontofSamuraiMag/tests/test_base_plate_body.py
git commit -m "Add build_base_plate_bolted (PartDesign Body with 8 ISO holes)"
```

---

## Phase 3 — Integration

### Task 10: Rewrite `build_detector_fixture` to assemble the three Bodies + fasteners

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/components.py` (replace body of `build_detector_fixture`)
- Create: `infrontofSamuraiMag/tests/test_detector_fixture_assembly.py`

- [ ] **Step 1: Write failing tests**

```python
# infrontofSamuraiMag/tests/test_detector_fixture_assembly.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def _load():
    from ifsm.config import load_build_config
    from ifsm.layout import compute_detector_placements
    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = compute_detector_placements(cfg.geometry)
    return cfg.geometry, placements


def test_fixture_returns_three_bodies_and_fasteners() -> None:
    import FreeCAD as App
    from ifsm.components import build_detector_fixture

    geom, placements = _load()
    doc = App.newDocument("TestFix")
    result = build_detector_fixture(doc, geom, placements[0])
    assert set(result.keys()) >= {"weldment", "upper_clamp", "base_plate", "fasteners"}
    for key in ("weldment", "upper_clamp", "base_plate"):
        assert len(result[key].Shape.Solids) == 1, f"{key} is not single-solid"
    assert len(result["fasteners"]) > 0


def test_fixture_bolt_count_matches_config() -> None:
    import FreeCAD as App
    from ifsm.components import build_detector_fixture

    geom, placements = _load()
    doc = App.newDocument("TestFix2")
    result = build_detector_fixture(doc, geom, placements[0])
    # 4 clamp bolts + 4 plate-side bolts + 4 weldment-side bolts per fixture
    bolt_solids = [f for f in result["fasteners"] if f["kind"] == "bolt"]
    assert len(bolt_solids) == 12


def test_all_12_fixtures_build_cleanly() -> None:
    import FreeCAD as App
    from ifsm.components import build_detector_fixture

    geom, placements = _load()
    doc = App.newDocument("TestFix12")
    assert len(placements) == 12
    for i, p in enumerate(placements):
        result = build_detector_fixture(doc, geom, p, name_suffix=f"_{i}")
        for key in ("weldment", "upper_clamp", "base_plate"):
            assert len(result[key].Shape.Solids) == 1, f"placement {i} key {key}"


def test_fixture_honors_draw_fasteners_flag() -> None:
    import FreeCAD as App
    from ifsm.components import build_detector_fixture
    from dataclasses import replace

    geom, placements = _load()
    clamp_no_fasteners = replace(geom.detector.clamp, draw_fasteners_as_solids=False)
    detector_no = replace(geom.detector, clamp=clamp_no_fasteners)
    geom_no = replace(geom, detector=detector_no)
    doc = App.newDocument("TestFixFlag")
    result = build_detector_fixture(doc, geom_no, placements[0])
    assert result["fasteners"] == []
```

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_detector_fixture_assembly.py
```

Expected: FAIL (old `build_detector_fixture` has different return signature).

- [ ] **Step 3: Rewrite `build_detector_fixture`**

Locate `def build_detector_fixture(` (line ~1488 of `components.py`). Replace its body with:

```python
def build_detector_fixture(
    doc,
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    name_suffix: str = "",
) -> dict:
    """Return a dict of named Bodies + fastener solids for one detector position.

    Returned shape:
        {
            "weldment": PartDesign::Body,
            "upper_clamp": PartDesign::Body,
            "base_plate": PartDesign::Body,
            "fasteners": [ {kind: str, size: str, solid: Part.Shape, placement: ...}, ... ],
        }

    Fasteners are simplified Part primitives (see primitives_fasteners.py) and
    are only produced if `cfg.detector.clamp.draw_fasteners_as_solids` is True.
    """
    from .primitives_fasteners import make_hex_socket_bolt, make_hex_nut, make_flat_washer

    weldment = build_weldment_load_bearing(doc, cfg, placement, name_suffix=name_suffix)
    upper_clamp = build_upper_clamp_detachable(doc, cfg, placement, name_suffix=name_suffix)
    base_plate = build_base_plate_bolted(doc, cfg, placement, name_suffix=name_suffix)

    fasteners: list[dict] = []
    clamp_cfg = cfg.detector.clamp
    if clamp_cfg.draw_fasteners_as_solids:
        layout = detector_fixture_geometry(cfg, placement)
        try:
            clamp_thread = _bolt_diameter_to_thread(clamp_cfg.clamp_bolt_diameter_mm)
        except KeyError:
            clamp_thread = "M6"
        try:
            plate_thread = _bolt_diameter_to_thread(clamp_cfg.mount_bolt_hole_diameter_mm)
        except KeyError:
            plate_thread = "M8"

        # Clamp bolts (4): along clamp_bolt_axis, through upper + lower halves
        for center in layout.clamp_bolt_centers:
            head_seat = center  # treat centers as head seat
            bolt = make_hex_socket_bolt(
                size=clamp_thread,
                shank_length_mm=2.0 * clamp_cfg.clamp_ear_thickness_mm + clamp_cfg.outer_diameter_mm,
                origin=head_seat,
                axis=layout.clamp_bolt_axis,
            )
            fasteners.append({"kind": "bolt", "size": clamp_thread, "solid": bolt,
                              "placement": placement.tag, "subtype": "clamp"})

        # Plate-side bolts (4)
        for center in layout.plate_hole_centers:
            bolt = make_hex_socket_bolt(
                size=plate_thread,
                shank_length_mm=clamp_cfg.mount_base_thickness_mm + 12.0,
                origin=center,
                axis=layout.mount_axis,
            )
            fasteners.append({"kind": "bolt", "size": plate_thread, "solid": bolt,
                              "placement": placement.tag, "subtype": "plate_side"})
            washer = make_flat_washer(plate_thread, center, layout.mount_axis)
            fasteners.append({"kind": "washer", "size": plate_thread, "solid": washer,
                              "placement": placement.tag, "subtype": "plate_side"})

        # Weldment-side bolts (4)
        for center in layout.base_hole_centers:
            bolt = make_hex_socket_bolt(
                size=plate_thread,
                shank_length_mm=clamp_cfg.mount_base_thickness_mm + 18.0,
                origin=center,
                axis=layout.mount_axis,
            )
            fasteners.append({"kind": "bolt", "size": plate_thread, "solid": bolt,
                              "placement": placement.tag, "subtype": "weldment_side"})
            nut = make_hex_nut(plate_thread, center, layout.mount_axis)
            fasteners.append({"kind": "nut", "size": plate_thread, "solid": nut,
                              "placement": placement.tag, "subtype": "weldment_side"})

    return {
        "weldment": weldment,
        "upper_clamp": upper_clamp,
        "base_plate": base_plate,
        "fasteners": fasteners,
    }
```

**Important**: search for every call site of the old `build_detector_fixture` in the codebase (likely in `assembly.py` and possibly elsewhere):

```bash
grep -rn "build_detector_fixture" infrontofSamuraiMag/src/
```

Update each call site to accept the new dict return:
- Where the old code did `housing, clamp_a, support_carrier, mount_base = build_detector_fixture(cfg, placement)`, replace with:

```python
    result = build_detector_fixture(doc, cfg, placement)
    weldment_shape = result["weldment"].Shape
    upper_clamp_shape = result["upper_clamp"].Shape
    base_plate_shape = result["base_plate"].Shape
    fastener_solids = [f["solid"] for f in result["fasteners"]]
```

The call site must now accept `doc` as well — thread the active document through if not already available.

- [ ] **Step 4: Run, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_detector_fixture_assembly.py
```

Expected: PASS. Also run the full pure-python suite to confirm no import-time regressions:

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q -m pure_python infrontofSamuraiMag/tests
```

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/components.py \
        infrontofSamuraiMag/src/ifsm/assembly.py \
        infrontofSamuraiMag/tests/test_detector_fixture_assembly.py
git commit -m "Rewrite build_detector_fixture to return 3 Bodies + fastener solids"
```

---

### Task 11: Add `detector_fixture_no_interpenetration` validator

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/validation.py`
- Create: `infrontofSamuraiMag/tests/test_fixture_interpenetration.py`

- [ ] **Step 1: Write failing tests**

```python
# infrontofSamuraiMag/tests/test_fixture_interpenetration.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def test_validator_passes_on_clean_fixture() -> None:
    import FreeCAD as App
    from ifsm.components import build_detector_fixture
    from ifsm.config import load_build_config
    from ifsm.layout import compute_detector_placements
    from ifsm.validation import detector_fixture_no_interpenetration

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = compute_detector_placements(cfg.geometry)
    doc = App.newDocument("TestValPass")
    result = build_detector_fixture(doc, cfg.geometry, placements[0])
    status, detail = detector_fixture_no_interpenetration(result, placement_tag=placements[0].tag)
    assert status == "pass", detail


def test_validator_fails_when_weldment_overlaps_base() -> None:
    """Construct an artificial overlap and verify the validator flags it."""
    import FreeCAD as App
    import Part
    from ifsm.validation import detector_fixture_no_interpenetration

    doc = App.newDocument("TestValFail")
    # Mock: build two overlapping cylinders as 'weldment' and 'base_plate'.
    weldment = doc.addObject("PartDesign::Body", "FakeWeldment")
    base = doc.addObject("PartDesign::Body", "FakeBase")
    cyl_a = Part.makeCylinder(5.0, 20.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    cyl_b = Part.makeCylinder(5.0, 20.0, App.Vector(0, 0, 10), App.Vector(0, 0, 1))  # overlaps by 10 mm
    # Wrap as pseudo-body-like objects for the test
    class FakeBody:
        def __init__(self, shape, name):
            self.Shape = shape
            self.Name = name
    result = {
        "weldment": FakeBody(cyl_a, "FakeWeldment"),
        "upper_clamp": FakeBody(Part.makeBox(1, 1, 1), "FakeUpper"),
        "base_plate": FakeBody(cyl_b, "FakeBase"),
        "fasteners": [],
    }
    status, detail = detector_fixture_no_interpenetration(result, placement_tag="synthetic")
    assert status == "fail"
    assert "weldment" in detail and "base_plate" in detail


def test_validator_whitelists_bolt_through_hole() -> None:
    """Small OCC artefacts on bolt-through-hole contact should be tolerated up to 1e-3 mm^3."""
    import FreeCAD as App
    import Part
    from ifsm.validation import detector_fixture_no_interpenetration

    class FakeBody:
        def __init__(self, shape, name):
            self.Shape = shape
            self.Name = name
    # Plate with hole, bolt that exactly mates (likely tiny but nonzero overlap from OCC).
    plate = Part.makeBox(20, 20, 5).cut(Part.makeCylinder(3.0, 5.2, App.Vector(10, 10, -0.1),
                                                          App.Vector(0, 0, 1)))
    bolt = Part.makeCylinder(3.0, 5.0, App.Vector(10, 10, 0), App.Vector(0, 0, 1))
    result = {
        "weldment": FakeBody(Part.makeBox(1, 1, 1), "FakeW"),
        "upper_clamp": FakeBody(Part.makeBox(1, 1, 1), "FakeU"),
        "base_plate": FakeBody(plate, "FakeP"),
        "fasteners": [{"kind": "bolt", "size": "M6", "solid": bolt, "placement": "x", "subtype": "plate_side"}],
    }
    status, _ = detector_fixture_no_interpenetration(result, placement_tag="synthetic")
    assert status == "pass"
```

- [ ] **Step 2: Run, expect RED**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_fixture_interpenetration.py
```

Expected: FAIL (ImportError — function missing).

- [ ] **Step 3: Implement the validator**

Append to `infrontofSamuraiMag/src/ifsm/validation.py`:

```python
def detector_fixture_no_interpenetration(
    fixture: dict,
    placement_tag: str,
    strict_tolerance_mm3: float = 1e-6,
    bolt_whitelist_tolerance_mm3: float = 1e-3,
) -> tuple[str, str]:
    """Validate that components of one fixture do not interpenetrate.

    Whitelist: (bolt, {weldment, upper_clamp, base_plate}) pairs use the looser
    `bolt_whitelist_tolerance_mm3` to allow OCC contact-face artefacts. All
    other pairs use strict zero-overlap tolerance.

    Returns (status, detail) where status is 'pass' or 'fail'.
    """
    import Part  # local import to avoid top-level FreeCAD dependency

    named_bodies = {
        "weldment": fixture["weldment"],
        "upper_clamp": fixture["upper_clamp"],
        "base_plate": fixture["base_plate"],
    }
    fasteners = fixture.get("fasteners", [])

    violations: list[str] = []

    body_items = list(named_bodies.items())
    # Body-vs-body: strict 0-tolerance
    for i in range(len(body_items)):
        for j in range(i + 1, len(body_items)):
            name_a, body_a = body_items[i]
            name_b, body_b = body_items[j]
            vol = _shape_interference_volume(body_a.Shape, body_b.Shape)
            if vol > strict_tolerance_mm3:
                violations.append(f"{name_a}↔{name_b} overlap={vol:.6f}mm³")

    # Body-vs-fastener: whitelist for bolts (kind='bolt'); strict for others
    for name, body in named_bodies.items():
        for fast in fasteners:
            vol = _shape_interference_volume(body.Shape, fast["solid"])
            tol = bolt_whitelist_tolerance_mm3 if fast["kind"] == "bolt" else strict_tolerance_mm3
            if vol > tol:
                violations.append(
                    f"{name}↔{fast['kind']}[{fast['size']},{fast.get('subtype','')}] overlap={vol:.6f}mm³"
                )

    # Fastener-vs-fastener: strict
    for i in range(len(fasteners)):
        for j in range(i + 1, len(fasteners)):
            fa, fb = fasteners[i], fasteners[j]
            vol = _shape_interference_volume(fa["solid"], fb["solid"])
            if vol > strict_tolerance_mm3:
                violations.append(
                    f"{fa['kind']}#{i}↔{fb['kind']}#{j} overlap={vol:.6f}mm³"
                )

    if violations:
        return "fail", f"[placement={placement_tag}] " + "; ".join(violations)
    return "pass", f"placement={placement_tag} all pairs within tolerance"
```

Now wire it into the strict validation gate. Find where existing fixture-level checks are run (grep for `build_detector_fixture` in `validation.py`). After each fixture is built, add:

```python
    status, detail = detector_fixture_no_interpenetration(fixture_result, placement.tag)
    checks.append(CheckResult(
        name="detector_fixture_no_interpenetration",
        status=status,
        detail=detail,
    ))
```

(Match the naming and structure of nearby `CheckResult` usages.)

- [ ] **Step 4: Run, expect GREEN**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_fixture_interpenetration.py
```

Expected: PASS all three tests.

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/validation.py \
        infrontofSamuraiMag/tests/test_fixture_interpenetration.py
git commit -m "Add detector_fixture_no_interpenetration validator with bolt-through whitelist"
```

---

## Phase 4 — Configs and Integration Regression

### Task 12: Add new fields to `afterSRC` and `infrontofSamuraiMag` configs

**Files:**
- Modify: `afterSRC/config/default_afterSRC.yaml`
- Modify: `infrontofSamuraiMag/config/default_infront.yaml`
- Modify: `infrontofSamuraiMag/config/profiles/legacy_center_preview_locked.yaml`
- Modify: `infrontofSamuraiMag/config/profiles/side_exit_single_rotary_strict.yaml`

- [ ] **Step 1: Patch `afterSRC/config/default_afterSRC.yaml`**

In the `detector.clamp:` section (around line 205), append these four lines (indented at the clamp children level):

```yaml
      fillet_radius_mm: 3.0
      chamfer_mm: 1.0
      bolt_head_type: ISO4762_hex_socket
      draw_fasteners_as_solids: true
```

- [ ] **Step 2: Patch `infrontofSamuraiMag/config/default_infront.yaml`**

Same change in its `detector.clamp:` section.

- [ ] **Step 3: Patch both profile YAMLs**

Append the same 4 lines to the `detector.clamp:` section of:
- `infrontofSamuraiMag/config/profiles/legacy_center_preview_locked.yaml`
- `infrontofSamuraiMag/config/profiles/side_exit_single_rotary_strict.yaml`

- [ ] **Step 4: Sanity check all configs load**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q \
  infrontofSamuraiMag/tests/test_config.py
```

Expected: PASS (new test from Task 3 exercises the new fields; backward-compat test from Task 3 exercises absence).

- [ ] **Step 5: Commit**

```bash
git add afterSRC/config/default_afterSRC.yaml \
        infrontofSamuraiMag/config/default_infront.yaml \
        infrontofSamuraiMag/config/profiles/legacy_center_preview_locked.yaml \
        infrontofSamuraiMag/config/profiles/side_exit_single_rotary_strict.yaml
git commit -m "Populate fillet/chamfer/bolt_head/draw_fasteners defaults in all clamp configs"
```

---

### Task 13: Strict-validate `afterSRC` and `infrontofSamuraiMag` + worklog entries

**Files:**
- Modify: `afterSRC/worklog.md` (append)
- Modify: `infrontofSamuraiMag/worklog.md` (append)
- Modify: `polarimeter/worklog.md` (append)

- [ ] **Step 1: Run afterSRC strict validate-only**

```bash
./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation
```

Expected: `status=pass` in `afterSRC/afterSRC.validation_report.json`. The new `detector_fixture_no_interpenetration` check must appear in the report and pass for all 12 placements.

- [ ] **Step 2: Run afterSRC full rebuild**

```bash
./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --force-rebuild
```

Expected: `status=pass`; FCStd + STEP artifacts regenerated.

- [ ] **Step 3: Run infrontofSamuraiMag strict validate-only**

```bash
./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation
```

Expected: `status=pass`.

- [ ] **Step 4: Run infrontofSamuraiMag full rebuild**

```bash
./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --force-rebuild
```

Expected: `status=pass`; FCStd + STEP regenerated.

- [ ] **Step 5: Run full pytest suite**

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q infrontofSamuraiMag/tests
```

Expected: all green.

- [ ] **Step 6: Append worklog entries**

Append to `afterSRC/worklog.md`:

```
- Timestamp UTC: <fill in>
- Timestamp Local: <fill in>
- Module/Scope: afterSRC full rebuild after Sub-2 clamp weldment redesign
- Command(s): `./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --force-rebuild`
- Key Parameters/Overrides: detector fixture now emits 3 single-solid PartDesign Bodies + real fastener solids; detector_fixture_no_interpenetration added to strict gate
- Validation Result: pass
- Artifacts/State: afterSRC/state.json.run.status=pass; FCStd + STEP regenerated; new `parts_manifest` block in validation_report.json
- Next Action: hand off for visual review per DoD §8 of the spec
```

Append equivalent entries to `infrontofSamuraiMag/worklog.md` and `polarimeter/worklog.md`.

- [ ] **Step 7: Commit**

```bash
git add afterSRC/ infrontofSamuraiMag/ polarimeter/worklog.md 2>/dev/null || \
  git add afterSRC/worklog.md afterSRC/afterSRC.FCStd afterSRC/afterSRC.step afterSRC/afterSRC.validation_report.json \
          afterSRC/state.json \
          infrontofSamuraiMag/worklog.md infrontofSamuraiMag/infrontofSamuraiMag.FCStd \
          infrontofSamuraiMag/infrontofSamuraiMag.step infrontofSamuraiMag/infrontofSamuraiMag.validation_report.json \
          infrontofSamuraiMag/state.json \
          worklog.md
git commit -m "Sub-2 regression: afterSRC + infrontofSamuraiMag strict-pass after clamp weldment rewrite"
```

---

## Phase 5 — Visual Review + DoD Sign-off

### Task 14: Visual review with before/after screenshots

**Files:**
- Create: `polarimeter/reports/sub2_before_after/before_afterSRC.png`
- Create: `polarimeter/reports/sub2_before_after/after_afterSRC.png`
- Create: `polarimeter/reports/sub2_before_after/before_ifsm.png`
- Create: `polarimeter/reports/sub2_before_after/after_ifsm.png`
- Create: `polarimeter/reports/sub2_before_after/review_notes.md`

- [ ] **Step 1: Capture "before" screenshots**

Before Task 10's rewrite, the old FCStd had primitive-soup fixtures. If the pre-rewrite FCStd is not saved in git, **reconstruct from git history**:

```bash
git stash   # if any WIP
git checkout HEAD~<N_commits_back> -- afterSRC/afterSRC.FCStd  # N = count of commits since Task 10
# Open in FreeCAD, screenshot zoomed on one detector fixture at 20.9° angle, save as reports/sub2_before_after/before_afterSRC.png
git checkout HEAD -- afterSRC/afterSRC.FCStd
```

Same for ifsm.

- [ ] **Step 2: Capture "after" screenshots**

Open the current FCStd in FreeCAD, screenshot the same fixture (same zoom, same orientation), save as `after_afterSRC.png` / `after_ifsm.png`.

- [ ] **Step 3: Write `review_notes.md`**

```markdown
# Sub-2 Visual Review Notes

- **Reviewed FCStd**: `afterSRC/afterSRC.FCStd`, `infrontofSamuraiMag/infrontofSamuraiMag.FCStd`
- **Reviewer**: <name>
- **Date**: 2026-04-17 (adjust)

## Confirmed

- All 12 detector fixtures have visible chamfers on external edges (width ≈ `chamfer_mm`)
- Fillets present at saddle↔ring, adapter↔saddle, upright↔bridge transitions
- Hex-socket bolt heads visible at clamp-bolt and plate-bolt positions
- Washers visible at plate-side positions; nuts visible at weldment-side positions
- Oblique channels (53.4° proton_large positions) — no obvious geometric clash
- Feature tree in FreeCAD shows PartDesign Body with Pad/Hole/Fillet/Chamfer features for each of the 3 bodies

## Open Items / Nits

- <fill in during review; expected to be empty or list minor cosmetic notes>

## Screenshots

- `before_afterSRC.png` vs `after_afterSRC.png`
- `before_ifsm.png` vs `after_ifsm.png`
```

- [ ] **Step 4: Commit**

```bash
git add polarimeter/reports/sub2_before_after/
git commit -m "Sub-2 visual review: before/after screenshots + review notes"
```

---

### Task 15: Emit `parts_manifest` + Sub-2 DoD sign-off

**Files:**
- Modify: `infrontofSamuraiMag/src/ifsm/validation.py` (add a `parts_manifest` emitter)
- Modify: `infrontofSamuraiMag/src/ifsm/export.py` (include manifest in the validation report JSON)
- Create: `docs/superpowers/specs/2026-04-17-sub2-dod-signoff.md`

- [ ] **Step 1: Add `parts_manifest` emitter**

In `validation.py`, add:

```python
def build_clamp_parts_manifest(cfg: GeometryConfig, placements: list) -> list[dict]:
    """Return per-fixture make/buy manifest entries for the clamp subsystem."""
    clamp_cfg = cfg.detector.clamp
    manifest: list[dict] = []
    for p in placements:
        manifest.append({
            "placement": p.tag,
            "parts": [
                {"name": "Weldment_LoadBearing", "make_or_buy": "make",
                 "material": "SUS304", "process": "weldment",
                 "notes": "lower half-clamp + saddle + adapter + twin uprights + top bridge"},
                {"name": "UpperClamp_Detachable", "make_or_buy": "make",
                 "material": "SUS304", "process": "machined"},
                {"name": "BasePlate_Bolted", "make_or_buy": "make",
                 "material": "A5052", "process": "plate"},
                {"name": "Bolt_clamp", "make_or_buy": "buy",
                 "spec": f"ISO 4762 M{int(clamp_cfg.clamp_bolt_diameter_mm)} SUS304",
                 "qty_per_fixture": 4},
                {"name": "Bolt_plate_side", "make_or_buy": "buy",
                 "spec": f"ISO 4762 M{int(clamp_cfg.mount_bolt_hole_diameter_mm)} SUS304",
                 "qty_per_fixture": 4},
                {"name": "Bolt_weldment_side", "make_or_buy": "buy",
                 "spec": f"ISO 4762 M{int(clamp_cfg.mount_bolt_hole_diameter_mm)} SUS304",
                 "qty_per_fixture": 4},
                {"name": "Nut_weldment_side", "make_or_buy": "buy",
                 "spec": f"ISO 4032 M{int(clamp_cfg.mount_bolt_hole_diameter_mm)} SUS304",
                 "qty_per_fixture": 4},
                {"name": "Washer_plate_side", "make_or_buy": "buy",
                 "spec": f"ISO 7089 M{int(clamp_cfg.mount_bolt_hole_diameter_mm)} SUS304",
                 "qty_per_fixture": 4},
            ],
        })
    return manifest
```

- [ ] **Step 2: Wire it into the report export**

In `export.py` (or wherever `validation_report.json` is serialized), add a top-level `parts_manifest` key with the list from `build_clamp_parts_manifest`.

- [ ] **Step 3: Regenerate reports**

```bash
./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --force-rebuild
./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --force-rebuild
```

Expected: `afterSRC/afterSRC.validation_report.json` and `infrontofSamuraiMag/infrontofSamuraiMag.validation_report.json` now include `parts_manifest` with 12 placements × 9 parts.

- [ ] **Step 4: Write DoD sign-off document**

```markdown
# Sub-2 Definition of Done — Sign-off

- **Spec**: `docs/superpowers/specs/2026-04-17-detector-clamp-weldment-redesign-design.md` §10
- **Plan**: `docs/superpowers/plans/2026-04-17-detector-clamp-weldment-redesign.md`
- **Date signed off**: 2026-04-17 (adjust)

| DoD # | Criterion | Evidence | Status |
|---|---|---|---|
| 1 | Phase 0 passed or carve-outs documented | `docs/superpowers/specs/2026-04-17-phase0-partdesign-spike-report.md` | <pass/carve-out> |
| 2 | 3 Bodies each single-solid for every placement | `test_weldment_body`, `test_upper_clamp_body`, `test_base_plate_body` all green | pass |
| 3 | Weldment feature tree has fillets + chamfers | `test_weldment_has_fillets_and_chamfers` green | pass |
| 4 | Fasteners as real solids, count matches config | `test_fixture_bolt_count_matches_config`, `test_fixture_honors_draw_fasteners_flag` | pass |
| 5 | `detector_fixture_no_interpenetration` green | `afterSRC/afterSRC.validation_report.json`, `infrontofSamuraiMag/.../validation_report.json` | pass |
| 6 | afterSRC + ifsm strict-validate pass | Task 13 worklog entries | pass |
| 7 | pytest suite green | Task 13 Step 5 | pass |
| 8 | Visual review: 12 fixtures look like machined parts | `polarimeter/reports/sub2_before_after/review_notes.md` | pass |
| 9 | `parts_manifest` in report JSON with make/buy tags | inspection of regenerated report | pass |
| 10 | Worklog entries appended (Phase 0 + final handoff) in both `polarimeter/worklog.md` and `infrontofSamuraiMag/worklog.md` | Task 2 Step 2 + Task 13 Step 6 | pass |

## Carve-outs (if any)

- <list any Phase 0 items that failed and the fallbacks used>

## Handoff

Sub-2 complete. Next sub-project in the manufacturability roadmap: **Sub-1 — Global pair-wise interference validator** (which elevates the `detector_fixture_no_interpenetration` pattern from per-fixture to whole-assembly scope). Separate spec + plan.
```

- [ ] **Step 5: Commit**

```bash
git add infrontofSamuraiMag/src/ifsm/validation.py \
        infrontofSamuraiMag/src/ifsm/export.py \
        afterSRC/afterSRC.validation_report.json \
        infrontofSamuraiMag/infrontofSamuraiMag.validation_report.json \
        docs/superpowers/specs/2026-04-17-sub2-dod-signoff.md
git commit -m "Sub-2 DoD sign-off: parts_manifest in report + all criteria evidenced"
```

- [ ] **Step 6: Delete the Phase 0 spike script**

```bash
git rm infrontofSamuraiMag/scripts/spike_partdesign_headless.py
git commit -m "Remove Phase 0 spike script (served its purpose, outcome in report)"
```

---

## Self-Review Summary (for the executor's reference)

- Spec §1 (context) — covered by the plan header, no dedicated task
- Spec §2 (goals/non-goals) — enforced throughout (e.g., Task 10 returns only the clamp dict; welds not drawn; 2D drawings not emitted)
- Spec §3 (Approach Y) — Tasks 6–10 implement PartDesign API usage
- Spec §4 (architecture / feature trees) — Tasks 7–9 build the three Bodies per the spec's skeleton
- Spec §5 (config additions + guard) — Tasks 3, 4, 12
- Spec §6 (Phase 0) — Tasks 1, 2
- Spec §7 (validator) — Task 11
- Spec §8 (tests + regression) — Tasks 3–13 interleave tests; Task 13 runs strict-validate; Task 14 captures visual review
- Spec §9 (code changes summary) — reflected in the per-task file lists
- Spec §10 (DoD) — explicitly checked off in Task 15
- Spec §11 (risks) — mitigations embedded: Task 1 for PartDesign risk, Task 4 for fillet radius guard, Task 10 for fastener flag fallback, Task 13 for regression cadence
- Spec §12 (open questions) — `_bolt_diameter_to_thread` helper answers the M-size derivation; dowel pins explicitly deferred (not in plan, as per spec)
- Spec §13 (next step) — DoD sign-off doc (Task 15) names Sub-1 as follow-on
