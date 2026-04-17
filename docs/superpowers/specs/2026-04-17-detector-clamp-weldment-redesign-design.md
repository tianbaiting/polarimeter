# Detector Clamp Weldment Redesign — Design Spec

- **Date**: 2026-04-17
- **Pilot module**: `afterSRC` (reuses `infrontofSamuraiMag/src/ifsm/` internals → `infrontofSamuraiMag` inherits automatically)
- **Scope**: Sub-project 2 of a 6-step decomposition (see §1)
- **Status**: Design approved, ready for implementation planning

## 0. Context

The DPOL polarimeter has three FreeCAD variants (`infrontofSamuraiMag/`, `afterSRC/`, `compactInVacuum/`). All three pass their current strict validation (angles, radii, vacuum boundary closed), but the models are **not yet engineering-manufacturable**:

- Parts are built as **pure geometric primitives** (`slit_prism`, `tube_shape`, etc.) booleaned together
- Several subsystems rely on **intentional solid interpenetration** to force FreeCAD's fuse to resolve them into one solid; `skip_overlap_checks` exists as a config flag, and pair-wise interference is only validated on a handful of hand-picked pairs
- No real machining features (fillets, chamfers, bolt heads, O-ring grooves modelled as placeholders with depth 0)

The user's two concrete pain points:
1. **Geometry interpenetration** — `validation_report.json=pass` does not actually mean "parts don't clash"
2. **Detector clamp fixture design is bad** — currently 6+ interpenetrating solids masquerading as what BLP_v1 explicitly freezes as "one integrated load-bearing part"

This spec addresses only the **detector clamp fixture** subsystem, as the first step in a staged path to manufacturability. Topology is kept at BLP_v1; only the implementation changes.

## 1. Project Decomposition (reference only)

Manufacturability work decomposes into 6 sub-projects, strictly ordered:

1. **Sub-1** Global pair-wise interference validator (independent)
2. **Sub-2** Detector clamp fixture redesign ← **this spec**
3. **Sub-3** Other subsystems (chamber shell stiffening, port nozzles, target rotary, stand) — design polish
4. **Sub-4** Engineering-review view generator (HTML/PDF with ortho/section views + key dims)
5. **Sub-5** BOM + make/buy classification output
6. **Sub-6** Pilot handoff (afterSRC → ifsm → compactInVacuum)

This spec covers Sub-2 only. Sub-1's acceptance rules (no pair-wise solid overlap beyond a designed whitelist) are **inlined** into Sub-2's validation scope, restricted to "within one detector fixture".

## 2. Goals and Non-Goals

### Goals
- G1: Each detector fixture output is a clean set of **3 named PartDesign Body solids** + fastener solids, with no intentional interpenetration
- G2: Real machining features present: fillets, chamfers, counterbored/hex-socket bolt holes
- G3: Fasteners (bolts/nuts/washers) are drawn as real solids to required ISO proportions
- G4: A new validator proves zero interpenetration within any single fixture (bolt-through-hole whitelisted)
- G5: Visual review of the FCStd shows 12 clamps that **look like machined parts**, not boolean-fused primitive stacks
- G6: Delivery target = L3 internal review (Sub-2 emits make/buy labels for clamp parts; full BOM is Sub-5)

### Non-Goals (explicit)
- NG1: **No change to BLP_v1 frozen topology.** The load-bearing weldment stays: support-side half clamp + saddle + transition block + twin uprights + top bridge. Detachable upper half-clamp and bolted base plate stay separate parts.
- NG2: **No welds drawn.** Weld joints are captured only in BOM notes; no fillet-weld geometry.
- NG3: **No 2D engineering drawings** (TechDraw output is Sub-4).
- NG4: **No full BOM.** Sub-2 emits a clamp-subsystem `parts_manifest` only.
- NG5: **No global (cross-fixture, cross-subsystem) interference check.** Sub-2 only validates within-one-fixture. Full global check is Sub-1.
- NG6: **No change to `detector_fixture_geometry()` placement logic.** 12 positions unchanged.
- NG7: **`compactInVacuum` out of scope.** Its detector mounting is undefined; it does not consume ifsm's clamp code.

## 3. Chosen Approach (of three considered)

Approach **Y — PartDesign API (Body + Pad/Pocket/Hole/Fillet features)**. Alternatives considered and rejected:

- **Approach X — Part primitives with non-overlapping booleans + `Shape.makeFillet`**: OCC's `makeFillet` on boolean results is brittle (null-face failures under some parameter combinations), and "weld-like fillets on booleaned primitives" does not actually communicate a weldment.
- **Approach Z — Hand-modeled reference FCStd + parametric placement**: Breaks the project's "code is ground truth" invariant (the whole `state.json` / hash-skip / strict-validation pipeline assumes code regenerates geometry). Rejected.

**Why Y wins**: PartDesign Body maps 1:1 to BLP_v1's "one integrated load-bearing part" semantics. Feature tree (Pads/Fillets/Holes) is visible in FreeCAD GUI for reviewers. Fillets/chamfers are applied to named Body edges, which is far more stable than on generic boolean results. Parametric code-as-truth is preserved.

**Risk hedge**: Phase 0 spike (§6) verifies PartDesign works in headless `freecadcmd` before committing to full Sub-2. Any sub-feature that fails falls back to Approach X locally, with a documented carve-out.

## 4. Architecture

### 4.1 Per-position deliverables

Each of the 12 detector positions emits:

| # | Name | Type | Content | make/buy |
|---|---|---|---|---|
| 1 | `Weldment_LoadBearing` | `PartDesign::Body` | lower half-clamp ring + anti-rotation key + lower saddle + transition (adapter) block + twin uprights + top bridge — **one Body, one Solid** | make (SUS304 weldment) |
| 2 | `UpperClamp_Detachable` | `PartDesign::Body` | upper half-clamp ring + ears + bolt holes — **one Body, one Solid** | make (SUS304 machined) |
| 3 | `BasePlate_Bolted` | `PartDesign::Body` | 4-hole base plate (plate-side bolt pattern + weldment-side receiving holes) — **one Body, one Solid** | make (A5052 plate) |
| 4..N | `Bolt_M{6,8}_#k`, `Nut_#k`, `Washer_#k` | simplified `Part` primitives | hex-socket head + shank + nut + washer, ISO proportions | buy (ISO 4762 / ISO 4032 / ISO 7089, SUS304) |

Scale: ~3 Body + ~8 bolt groups per position × 12 positions ≈ 300 solids total. Acceptable for FCStd/STEP export; re-evaluate if export > 30 s (see §8 risks).

### 4.2 Feature-tree skeleton (Weldment_LoadBearing)

```
Body_Weldment_LoadBearing
├─ Sketch_HalfRing        (split-plane profile of lower half-ring)
├─ Pad_HalfRing
├─ Sketch_AntiRotationKey
├─ Pad_AntiRotationKey
├─ Sketch_Saddle
├─ Pad_Saddle
├─ Sketch_AdapterBlock
├─ Pad_AdapterBlock
├─ Sketch_Uprights        (twin uprights in one sketch)
├─ Pad_Uprights
├─ Sketch_Bridge
├─ Pad_Bridge
├─ Hole_UprightsToBridge_[1..4]   (ISO threaded holes, PartDesign::Hole)
├─ Fillet_SaddleToRing_R{r}
├─ Fillet_AdapterToSaddle_R{r}
├─ Fillet_UprightsToBridge_R{r}
└─ Chamfer_ExternalEdges_C{c}
```

**Discipline**: adjacent Pads share coplanar mating faces; no 1 mm intentional bite. The Body's internal fuse is feature-tree-level, not boolean-level, so coplanar is sufficient.

### 4.3 Feature-tree skeleton (UpperClamp_Detachable)

```
Body_UpperClamp_Detachable
├─ Sketch_HalfRing        (upper half-ring, matches lower's split plane exactly)
├─ Pad_HalfRing
├─ Sketch_Ears            (two ears, sketched on ring outer face)
├─ Pad_Ears
├─ Hole_ClampBolt_[1..4]  (through-holes for split-bolts, counterbore on one side)
└─ Chamfer_ExternalEdges_C{c}
```

### 4.4 Feature-tree skeleton (BasePlate_Bolted)

```
Body_BasePlate_Bolted
├─ Sketch_PlateOutline
├─ Pad_Plate
├─ Hole_PlateSide_[1..4]    (bolt-through to plate.h / plate.v1 / plate.v2)
├─ Hole_WeldmentSide_[1..4] (bolt-through receiving the weldment's bottom bolts)
└─ Chamfer_CornerEdges_C{c}
```

### 4.5 Fastener solids

Fasteners are simplified primitives (not PartDesign Body) for performance:
- Shank: `Part.makeCylinder(d, L)`
- Hex-socket head: short cylinder with approximate proportions from ISO 4762
- Nut: hex prism built from a 6-wire profile — **basic hex prism is the chosen fidelity** (review-class, not drawing-class); faithful ISO 4032 proportions (chamfer top/bottom, thread depth) are deferred to Sub-4 if ever needed
- Washer: `tube_shape` (flat annulus)

One thin helper module `primitives_fasteners.py` owns this; `components.py` only calls helpers with `size={M6,M8}`, length, placement.

### 4.6 Edge selection for fillets/chamfers

Edges for `PartDesign::Fillet` are selected by **geometric query**, not by name:
- "Edges where face normals transition from `axis_u` to `axis_v` at a convex vertex" → a rib-to-face fillet
- "Edges on the outermost boundary of the external face set" → chamfer candidates

This survives the 12 different channel orientations without per-placement edge naming. A helper `select_edges_by_predicate(body, predicate_fn)` centralizes this.

## 5. Configuration Changes

Additions to `ClampConfig` and `AdapterBlockConfig` (in `infrontofSamuraiMag/src/ifsm/config.py`), with sensible defaults for backward compatibility:

| Field | Default | Purpose |
|---|---|---|
| `fillet_radius_mm` | `3.0` | Saddle↔ring, adapter↔saddle, upright↔bridge inner fillets |
| `chamfer_mm` | `1.0` | External edge chamfer |
| `bolt_head_type` | `"ISO4762_hex_socket"` | Head geometry family |
| `draw_fasteners_as_solids` | `true` | Master switch; set `false` to revert to holes-only if performance requires |

Existing fields (`outer_diameter_mm`, `clamp_ear_width_mm`, `mount_bolt_pitch_u_mm`, etc.) are **unchanged**. `afterSRC/config/default_afterSRC.yaml` and `infrontofSamuraiMag/config/profiles/*.yaml` gain the new fields at defaults.

**Validation guard**: at config-load, assert `fillet_radius_mm ≤ min(adjacent face spans) / 2` to prevent Fillet feature failure. If invalid, fail fast with a clear error.

## 6. Phase 0: Headless PartDesign Feasibility Spike

**Purpose**: before investing in the full rewrite, verify that `freecadcmd` (headless) can drive the PartDesign features we need. Time-box: 1–2 days.

**Location**: `infrontofSamuraiMag/scripts/spike_partdesign_headless.py` (throwaway, to be deleted after Sub-2 merges).

**Verification checklist**:

| # | Capability | Pass criterion |
|---|---|---|
| 0.1 | Create `PartDesign::Body` | `addObject` returns non-null |
| 0.2 | Create `Sketcher::SketchObject`, constrain closed profile | `Sketch.Shape.isValid()` |
| 0.3 | Add `PartDesign::Pad` from sketch | Body produces a single solid |
| 0.4 | Add `PartDesign::Hole` with ISO thread spec | Hole's `ThreadType`/`ThreadSize` round-trip |
| 0.5 | Add `PartDesign::Fillet` on a geometric-query-selected edge | No null-face; Body still has 1 solid |
| 0.6 | Export via `Body.Shape` → STEP | `len(body.Shape.Solids) == 1`; STEP round-trips |

**Fallback rule**: if any item fails, the corresponding feature reverts to Approach X (Part primitives + OCC fillet) for that feature only, with an explicit carve-out note in the final implementation. If 0.6 fails outright, this spec is re-opened.

**Deliverable**: a short markdown report (`docs/superpowers/specs/2026-04-17-phase0-partdesign-spike-report.md`) with pass/fail per item. Phase 0 outcome gates the rest of Sub-2.

## 7. Validation

### 7.1 New validator: `detector_fixture_no_interpenetration`

Added to `infrontofSamuraiMag/src/ifsm/validation.py`, runs under `--strict-validation`.

For each of the 12 placements:
- Collect the fixture's solids: `{Weldment, UpperClamp, BasePlate, Bolt_1..k, Nut_1..k, Washer_1..k}`
- For every unordered pair `(a, b)` with `a != b`, compute `overlap = _shape_interference_volume(a, b)`
- **Whitelist**: `(Bolt_k, X)` where `X ∈ {Weldment, UpperClamp, BasePlate}` — bolts pass through holes; face contact may register as tiny OCC artefact, so the tolerance for these pairs is `overlap ≤ 1e-3 mm³`
- **Zero tolerance** elsewhere: `overlap ≤ 1e-6 mm³`
- Any violation → `status=fail` with detail listing `(placement.tag, pair_a, pair_b, overlap_volume)`

### 7.2 Existing validators

No changes to existing checks. The new check is **additive**. The existing LOS-scope freeze (chamber shell, end modules, target hardware exempt from LOS checks) stays intact.

## 8. Testing

### 8.1 Unit tests (added to `infrontofSamuraiMag/tests/`)

| Test | Assertion |
|---|---|
| `test_weldment_is_single_solid` | `len(fixture['Weldment_LoadBearing'].Shape.Solids) == 1` for each placement |
| `test_upper_clamp_is_single_solid` | same |
| `test_base_plate_is_single_solid` | same |
| `test_fixture_internal_no_interpenetration` | intra-fixture pair-wise overlap_volume within tolerance; bolt-through whitelisted |
| `test_all_12_fixtures_build_cleanly` | 12 placements all build + individually pass the above |
| `test_weldment_has_fillets_and_chamfers` | feature tree contains ≥ 2 `PartDesign::Fillet` and ≥ 1 `PartDesign::Chamfer` |
| `test_bolt_count_matches_config` | per-fixture bolt solid count = value derived from `ClampConfig` |
| `test_config_backward_compat` | pre-existing config (no new fields) loads and builds using defaults |
| `test_fillet_radius_guard` | loading a config with `fillet_radius_mm > half-face-span` raises a clear error |

### 8.2 Integration regression

Both must pass after Sub-2:
- `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation` → `pass`
- `./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation` → `pass`
- `pytest -q infrontofSamuraiMag/tests` → all green

`compactInVacuum` is **not** required to regress (it does not consume ifsm's clamp).

### 8.3 Visual review (not automated, required for DoD)

Open the rebuilt FCStd for `afterSRC` in the FreeCAD GUI. Confirm **by inspection**:
- All 12 clamp fixtures visibly have chamfers on external edges and fillets at saddle/adapter/upright transitions
- Bolts/nuts/washers are visible as real hex-socket head solids with washers
- No obvious geometric clashes even at oblique channels (53.4° large-angle proton positions are historically the worst offenders)
- Capture a before/after screenshot pair in `reports/sub2_before_after/` for the worklog entry

## 9. Code Changes (summary)

| File | Change |
|---|---|
| `infrontofSamuraiMag/src/ifsm/components.py` | Rewrite `build_detector_fixture()`; signature preserved; returned shapes now come from PartDesign Bodies. `detector_support_clearance_mask` / `detector_support_package_mask` stay untouched. |
| `infrontofSamuraiMag/src/ifsm/primitives.py` | Add `partdesign_body_pad_from_profile()`, `partdesign_body_hole()`, `partdesign_fillet_on_edges()` helpers |
| `infrontofSamuraiMag/src/ifsm/primitives_fasteners.py` | **New**: hex-socket bolt, hex nut, flat washer builders as simplified `Part` solids |
| `infrontofSamuraiMag/src/ifsm/config.py` | Add `fillet_radius_mm`, `chamfer_mm`, `bolt_head_type`, `draw_fasteners_as_solids` to `ClampConfig` with defaults |
| `infrontofSamuraiMag/src/ifsm/validation.py` | Add `detector_fixture_no_interpenetration` check |
| `infrontofSamuraiMag/tests/` | Add tests per §8.1 |
| `infrontofSamuraiMag/scripts/spike_partdesign_headless.py` | **New (temporary)**: Phase 0 spike script, removed after Sub-2 merge |
| `afterSRC/config/default_afterSRC.yaml` | Add new fields with defaults |
| `infrontofSamuraiMag/config/profiles/*.yaml` | Same |
| `docs/superpowers/specs/2026-04-17-phase0-partdesign-spike-report.md` | **New**: Phase 0 outcome report |

## 10. Definition of Done

Sub-2 is complete when:

1. Phase 0 passed, or carve-outs for failing items are documented in the spike report
2. The three Bodies each present `len(Body.Shape.Solids) == 1` for every placement
3. Feature tree of the weldment shows at least the fillets and chamfers listed in §4.2
4. Fasteners appear as real solids (count matches config) — or `draw_fasteners_as_solids=false` is chosen with the reason recorded
5. `detector_fixture_no_interpenetration` passes for all 12 placements
6. afterSRC + infrontofSamuraiMag strict-validate both pass
7. `pytest -q infrontofSamuraiMag/tests` all green
8. Visual review pass: 12 fixtures look like machined parts; before/after screenshots in `reports/sub2_before_after/`
9. A `parts_manifest` block is added to the clamp subsystem's `validation_report.json` contribution, tagging each Body/fastener as `make` or `buy` with material or ISO spec
10. Two worklog entries appended (one for Phase 0 spike, one for final handoff) in both `polarimeter/worklog.md` and `infrontofSamuraiMag/worklog.md`

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| PartDesign headless API instability | Phase 0 spike validates upfront; local Approach X fallback |
| Sketch constraints brittle under config changes | Minimal sketches (no redundant constraints); all dims injected from config |
| `Fillet` radius > adjacent face half-span → feature fails | Config-load guard asserts `fillet_radius_mm ≤ min_adjacent_span / 2` |
| Geometric edge selection picks wrong edges at oblique channels | `select_edges_by_predicate` helper returns edge list; tests assert expected edge count per placement |
| 300 solids → slow STEP export | Threshold check: if export > 30 s, set `draw_fasteners_as_solids=false` and document |
| Intentional-overlap code elsewhere in `components.py` assumed clamp overlaps | Audit `_shape_interference_volume` call sites during rewrite; any fixture-related overlap assumptions update to "should not overlap" |
| `afterSRC/infrontofSamuraiMag` worklog regression cadence | Both configs regenerate during Sub-2; failing regressions treated as Sub-2 blockers, not Sub-3 tech-debt |

## 12. Open Questions (to resolve in implementation plan, not here)

- Exact ISO spec for default bolts (M6 vs M8 choice per joint) — follow `ClampConfig.mount_bolt_hole_diameter_mm` + `clamp_bolt_hole_diameter_mm` to back out size
- Whether to include alignment pins (dowel pins) in the base-plate-to-plate interface — defer to Sub-3 (plate subsystem polish) unless the clamp's positional repeatability needs them
- Whether the upper clamp's ear counterbore depth should be derived from bolt head height + clearance or set explicitly — lean explicit for drawing clarity, settle in plan

## 13. Next Step After This Spec

On user approval of this spec file:
- Invoke `superpowers:writing-plans` to produce the step-by-step implementation plan from §9 + §10, sequenced after Phase 0
