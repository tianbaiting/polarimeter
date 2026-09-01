# Sub-2 Visual Review Notes

> **ARCHIVED HISTORICAL REVIEW (2026-04-24).** The FCStd paths and commands below refer to the former
> root layout of the external H+V+V models. This evidence is not a review of either current
> CompactInVacuum baseline instrument; use `codex_targets.yaml` for current locations.

- **Reviewed FCStd**: `afterSRC/afterSRC.FCStd`, `infrontofSamuraiMag/infrontofSamuraiMag.FCStd`
- **Reviewer**: automated (artifact + Document.xml inventory); pending human GUI sign-off
- **Date**: 2026-04-24
- **Plan**: `docs/superpowers/plans/2026-04-17-detector-clamp-weldment-redesign.md` Task 14
- **Git head at export**: `90a1e35`

## Scope

Review the geometry change introduced by Tasks 1–12 of the detector-clamp weldment redesign plan — the primitive-soup fixture per detector position is replaced by three explicit PartDesign-equivalent bodies (Weldment_LoadBearing, UpperClamp_Detachable, BasePlate_Bolted) plus discrete fastener hardware, with chamfers and fillets on exposed edges.

## Inventory (Document.xml, post-rebuild)

| Module | Total Part::Feature objects |
| --- | --- |
| afterSRC | 330 |
| infrontofSamuraiMag | 324 |

### afterSRC detector-fixture counts

| Family | Count | Per-position |
| --- | --- | --- |
| `Weldment_LoadBearing_<sector>_<channel>` | 12 | 1 × 12 positions |
| `UpperClamp_Detachable_<sector>_<channel>` | 12 | 1 × 12 positions |
| `BasePlate_Bolted_<sector>_<channel>` | 12 | 1 × 12 positions |
| `DetectorFastener_…_clamp_bolt_M6_*` | 48 | 4 × 12 positions |
| `DetectorFastener_…_plate_side_bolt_M8_*` | 48 | 4 × 12 positions |
| `DetectorFastener_…_plate_side_washer_M8_*` | 48 | 4 × 12 positions |
| `DetectorFastener_…_weldment_side_nut_M8_*` | 48 | 4 × 12 positions |
| `DetectorHousing_<sector>_<channel>` | 12 | 1 × 12 positions |

Positions = 4 sectors (`left`, `right`, `up`, `down`) × 3 channels (`deuteron`, `proton_large`, `proton_small`) = 12; matches BLP v1 baseline.

Per-position bolt/nut/washer arithmetic: 4 clamp bolts (M6, top-down into clamp-to-weldment flange) + 4 plate-side stacks (M8 bolt + washer → through BasePlate → captive nut welded to weldment) = 4 + 4×3 = 16 fastener objects. × 12 positions = 192, matches Document.xml count.

### infrontofSamuraiMag deltas

Same detector-fixture family counts (324 total vs. 330 is explained by the different vacuum interface hardware: VF100 + VG80 + 4 side ports instead of afterSRC's ICF114 + ICF70).

## Confirmed against spec

- [x] 12 detector positions with identical `Weldment + UpperClamp + BasePlate` triplets (per-position names derived from `{sector}_{channel}`).
- [x] Fastener set per position is 16 objects (4 clamp + 4 plate bolt + 4 plate washer + 4 weldment nut). No stray fasteners, no missing ones.
- [x] Fastener thread-diameter mapping holds: clamp bolts `M6`, plate stack `M8`. (Document.xml names carry suffix `_M6_*` / `_M8_*`.)
- [x] Validation report `detector_fixture_no_interpenetration` checks present and pass for all 12 positions, strict=true, in both modules (see `afterSRC.validation_report.json`, `infrontofSamuraiMag.validation_report.json`).
- [x] STEP export enumerates 96,142 entities (afterSRC), confirming the solid bodies were flattened correctly for downstream CAD.
- [x] Pipeline runs under `IFSM_SKIP_FCSTD_ROUNDTRIP=1` with strict validation passing; both modules force-rebuilt cleanly from target.yaml.
- [x] Pytest suite: 40 passed, 33 skipped (skipped = FreeCAD-runtime-only tests).

## Pending items (need GUI review)

These require opening the FCStd in the FreeCAD GUI and visually inspecting — they cannot be verified from Document.xml alone:

- [ ] Visible chamfers on external edges of `Weldment_LoadBearing` (width ≈ `chamfer_mm` from config).
- [ ] Fillets at saddle↔ring, adapter↔saddle, upright↔bridge transitions.
- [ ] Hex-socket bolt heads actually rendered as hex geometry (not placeholder) at clamp-bolt and plate-bolt positions.
- [ ] Washers + nuts visible and co-located with plate-side/weldment-side bolt shafts.
- [ ] Oblique channels at `proton_large` (53.4°) positions — no visible clash between clamp halves, fasteners, and detector housing.
- [ ] Feature tree: 3 bodies per position with Pad/Hole/Fillet/Chamfer features (or Path-B `Part::Feature` wrappers — either is acceptable per Task 10 outcome).

## Screenshot capture (deferred)

The plan's before/after PNGs (`before_afterSRC.png`, `after_afterSRC.png`, `before_ifsm.png`, `after_ifsm.png`) are not produced here. Reasons:

1. FCStd files are gitignored, so "before" cannot be recovered by `git checkout -- *.FCStd`; would need a full checkout to pre-Task-10 code + rebuild (~10 min × 2 modules).
2. `IFSM_SKIP_FCSTD_ROUNDTRIP=1` means the exported FCStds have no `GuiDocument.xml`; opening in GUI will show default visibility + camera (fine for review, but camera framing must be set manually per position).
3. Offscreen Coin3D rendering at 330 viewprovider scale deadlocks in futex (FreeCAD #22870 class bug), so automation via `freecadcmd` + SoOffscreenRenderer is not viable at this scale.

Capture instructions for human reviewer (with FreeCAD GUI + MCP RPC server running):

```
# After — current head
FreeCAD GUI: open afterSRC/afterSRC.FCStd, zoom to one detector fixture at 20.9° (down_deuteron),
  screenshot → reports/sub2_before_after/after_afterSRC.png
Same for infrontofSamuraiMag/infrontofSamuraiMag.FCStd → after_ifsm.png

# Before — pre-Task-10 reconstruction
git log --oneline -- infrontofSamuraiMag/src/ifsm/components.py | find commit before Task 10 (object count 132)
git worktree add /tmp/sub2-before <commit-before-task-10>
cd /tmp/sub2-before && IFSM_SKIP_FCSTD_ROUNDTRIP=1 ./afterSRC/run_afterSRC.sh --force-rebuild
Open the resulting FCStd, same camera framing → before_afterSRC.png / before_ifsm.png
git worktree remove /tmp/sub2-before
```

## Open Items / Nits

- None identified from static inventory. Human GUI review may add cosmetic notes.
