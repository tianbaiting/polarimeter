# CompactInVacuum to CompactOne Migration

The module directory and stateful runner retain the `compactInVacuum` name for compatibility. The preferred architecture is now CompactOne.

| Legacy concept | CompactOne mapping | Migration state |
|---|---|---|
| `detector.diameter_mm` | `detector.active.diameter_mm` | compatibility scalar generated from schema v2 |
| `detector.length_mm` | `detector.active.thickness_mm` | compatibility scalar generated from schema v2 |
| one detector cylinder | active plastic + optics + SiPM + cassette components | preferred golden-cassette geometry implemented |
| annular clamp | cassette shell, insertion stop, key, mount datum | legacy reference only |
| twelve independent support arms | four three-channel sector cartridges | legacy selectable until artifact migration closes |
| `inner_frame` | sector cartridge rails/backbone/thermal bus | compatibility values generated from schema v2 |
| `top_services.rotary` | common target subsystem + deployment feedthrough layout | compatibility mapping generated |
| `top_services.electrical` | common services + deployment service-port layout | compatibility mapping generated |
| square-only vessel contract | selected deployment chamber candidate | removed from preferred validation |
| ICF annular solids | purchased-part contracts + project transitions + CAD envelopes | interface-envelope geometry only |
| WORK + PARK endpoint | WORK + PARK + complete motion sweep | preferred target validation required |
| center-ray/cylindrical LOS | target-region-to-active-disc acceptance cone | preferred LOS validation required |
| aggregate geometry checks | categorized strict/non-strict validation | preferred validator required |
| one whole-instrument artifact | cassette, golden sector, internal machine, and two deployment artifacts | required |

Configuration migration:

- Common platform: `config/common_detector.yaml`
- CompactOne afterSRC: `config/afterSRC_compact.yaml`
- CompactOne in front of SAMURAI: `config/infrontSamurai_compact.yaml`
- Stable alias afterSRC: `config/compact_one_afterSRC.yaml`
- Stable alias SAMURAI: `config/compact_one_infrontSamurai.yaml`
- Legacy scaffold: `config/default_compactInVacuum.yaml`

The old default remains available during staged geometry migration. It shall not be described as the preferred CompactOne design.
