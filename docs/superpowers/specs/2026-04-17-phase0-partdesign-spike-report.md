# Phase 0 — Headless PartDesign Feasibility Report

- **Date**: 2026-04-17
- **Spike script**: `infrontofSamuraiMag/scripts/spike_partdesign_headless.py`
- **Raw output**: `infrontofSamuraiMag/reports/phase0_spike/phase0_results.json`
- **FreeCAD version**: verbatim output of `freecadcmd --version`:

  ```
  FreeCAD 1.0.0 Revision:
  ```
- **Spike script commit**: `5ba2e39` (tip of Task 1 on main)

## Results

| # | Capability | Status | Detail |
|---|---|---|---|
| 0.1 | PartDesign::Body creation | pass | name=SpikeBody |
| 0.2 | Sketcher closed profile | pass | — |
| 0.3 | Pad → single-solid Body | pass | solids=1, volume=2000.000 mm³ |
| 0.4 | Hole with ISO threading | **fail** | ThreadSize=M3, solids=1, volume=1995.708, pre_hole_volume=1995.708, shrank=False — hole feature is a no-op in headless |
| 0.5 | Fillet on Body edge | pass | solids=1, volume=1995.708, base_volume=2000.000, shrank=True |
| 0.6 | Body → STEP export | pass | path=infrontofSamuraiMag/reports/phase0_spike/spike_body.step |

## Decision

- **If all pass**: proceed with Approach Y as planned (Tasks 3–15).
- **If 0.1 or 0.2 or 0.3 or 0.6 fail**: STOP. Re-open spec. Do not proceed to Task 3.
- **If 0.4 fails (Hole)**: carve-out — replace `PartDesign::Hole` with `PartDesign::Pocket` fed by a circular sketch; BOM text records the thread spec instead of the feature.
- **If 0.5 fails (Fillet)**: carve-out — emit Bodies without fillets, add Part-level `shape.makeFillet(r, edges)` after Body finalization. Accept OCC fragility risk; record test flakes if they surface.

**Result**: 0.4 failed (Hole no-op). 0.1/0.2/0.3/0.5/0.6 all pass. **Proceeding with Approach Y under the 0.4 Hole carve-out.**

## Carve-outs

- **Hole → Pocket + circular sketch**: The `PartDesign::Hole` feature is a silent no-op in headless `freecadcmd` on FreeCAD 1.0.0 (object creates, accepts `ThreadSize="M3"`, but recompute leaves body volume bit-exact — zero material removed). Task 5 (fastener primitives) and Task 6 (PartDesign helpers) must expose `add_hole` backed by `PartDesign::Pocket` fed by a circular `Sketcher` profile (not `PartDesign::Hole`). Thread specification (e.g., "M3×5") is recorded in the Body's Label/Description and/or BOM text instead of as a Hole feature property. Task 11's `detector_fixture_no_interpenetration` validator must verify volume actually decreased after a hole cut.

  The failure mode is the material cut, not the threading metadata: `ThreadSize` round-trips correctly but the Hole feature's Pocket operation does nothing. Non-threaded `PartDesign::Hole` usages were not separately tested, but the carve-out applies to all `PartDesign::Hole` usage in the headless pipeline regardless of threading.
- **FreeCAD 1.0 API drift absorbed into the spike**: `Sketcher.Support` → `AttachmentSupport` (with `Support` fallback), `Hole.Depth/DepthValue` → `DepthType/Depth` split, `Fillet.Base` takes `(body, [edge_names])` not `(body.Shape, …)`. Production code in `primitives.py` must use the FreeCAD 1.0 forms.
- **`freecadcmd` script invocation**: On FreeCAD 1.0, `freecadcmd <script>` loads scripts as modules, not `__main__`. Production scripts that need `main()` to run must call it unconditionally. `sys.exit()` also does not propagate to the shell under `freecadcmd`; wrapping scripts / tests should read JSON artifacts for pass/fail signal.
- **Fillet TopoNaming noise**: FreeCAD 1.0 emits `Invalid edge link` / `graph must be a DAG` warnings during Fillet recompute even when the Fillet operation succeeds and volume drops as expected. Downstream tests and the Task 11 validator should check volume delta and face count, not stderr cleanliness.

## Next

- Proceed to Task 3 (Extend DetectorClampConfig) under Approach Y with the above carve-outs applied in Tasks 5/6/11.
