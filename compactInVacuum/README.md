# CompactInVacuum Common Platform

The baseline comprises:

- `CompactInVacuum-afterSRC`
- `CompactInVacuum-preSAMURAI`

The `compactInVacuum/` and `CompactOne` names remain executable compatibility labels. External detector routes remain preserved legacy/reference implementations and are not modified by the common-platform redesign.

## Preferred hierarchy

`detector head -> three-channel sector holder -> four-sector internal assembly -> deployment chamber`

The old 35 mm nose, 44 mm cassette box, long cassette thermal bridge, independent wall rails, wall anchors, and temperature/housekeeping system are superseded.

## Detector head

The default prototype contains:

- 20.0 × 5.5 mm fast plastic active element;
- 0.25 mm reflector envelope;
- 0.50 mm optical coupling;
- 1.50 mm NDL EQR15-class SiPM package;
- 1.20 mm provisional sensor PCB/carrier;
- 1.00 mm rear mounting face;
- shallow light-tight sleeve;
- 3.0 mm short cable exit;
- separate 20.0 mm connector keepout.

Calculated physical housing depth:

`5.50 + 0.50 + 1.50 + 1.20 + 0.00 + 1.00 = 9.70 mm`

Cable and connector keepouts do not increase this metric. The default gate is 18.0 mm.

## Sector holder

One coherent carrier holds deuteron, small-angle proton, and large-angle proton heads. Each nest has an insertion stop, D-flat anti-rotation land, removable clamp bridge, and two provisional M3 fastener envelopes. One common plate provides acceptance relief, a rear cable lane, survey datums, and a plane–pin–slot chamber interface.

Heads remove rearward after clamp release. For the current afterSRC fixed-wall study, exact solid
poses validate only the first 12 mm inward release from the stationary support. The subsequent
translation, reorientation, and lift through the top ICF305 opening remain unresolved; the former
70 mm straight radial motion is not evidence of complete extraction.

The removable access closure owns no detector support, locating datum, protective-ground
termination, or permanent cable restraint. All holder load paths remain on stationary supports
that contact permanent chamber walls.

## Monitoring disposition

Dedicated temperature monitoring is removed. There is no physical sensor, temperature harness, required temperature channel, housekeeping capacity rule, or housekeeping feedthrough. Schema version 3 rejects the removed fields.

## Display roles

Physical and purchased-component/interface objects are visible by default. Keepouts, datums, service centerlines, physics acceptance, and optional reference objects are hidden. Active plastic, coupling, SiPM, carrier, housing, and holder have distinct inspection colors when GUI state is available.

## Configuration

- Common schema-v3 platform: `config/common_detector.yaml`
- afterSRC deployment: `config/afterSRC_compact.yaml`
- pre-SAMURAI deployment: `config/infrontSamurai_compact.yaml`
- legacy entry-point compatibility: `config/default_compactInVacuum.yaml`

See `MIGRATION.md` for rejected fields and mappings.

## Generation and validation

```bash
./compactInVacuum/run_freecad_tests.sh

./compactInVacuum/run_compactOne_prototypes.sh \
  ./compactInVacuum/config/afterSRC_compact.yaml \
  ./compactInVacuum/artifacts/prototypes

./compactInVacuum/run_compactOne_afterSRC.sh \
  --pipeline-index codex_targets.yaml \
  --force-rebuild

./compactInVacuum/run_compactOne_infrontSamurai.sh \
  --pipeline-index codex_targets.yaml \
  --force-rebuild
```

Non-strict validation permits documented evidence warnings but never geometry, collision, capacity,
or acceptance failures. A non-strict pass is a prototype geometry result, not a fabrication release.
Strict mode additionally requires supplier drawings, site envelopes, vacuum-material evidence,
chamber-access closure, and pressure-vessel analysis. It does not require removed monitoring hardware.

Generated CAD, screenshots, caches, and runtime state remain untracked unless intentionally selected as reference artifacts.

## Physics disposition

The redesign preserves 53.4° for the large-angle proton and 11.2° for the small-angle proton. Previously supplied nominal values of approximately 55.9° and 11.3° remain unresolved pending evidence.

## Authorities

- `docs/specs/compact_one_requirement_baseline.md`

Supporting records:

- `docs/specs/compact_one_architecture_audit.md`: dated implementation snapshot; later baseline
  revisions supersede conflicting extraction or access claims.
- `compactInVacuum/MIGRATION.md`: schema migration guide, not a mechanical requirement authority.
