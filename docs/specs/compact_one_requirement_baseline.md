# CompactInVacuum Requirement Baseline v2

## 1. Authority and scope

This document is the requirement authority for the common CompactInVacuum detector platform and its two baseline deployments:

1. `CompactInVacuum-afterSRC`, downstream of SRC.
2. `CompactInVacuum-preSAMURAI`, upstream of the SAMURAI terminal.

Both deployments place the compact plastic-scintillator detector heads, SiPM packages, passive internal services, and sector holders inside vacuum. Detector technology and common mechanical architecture are shared. Chamber geometry, purchased beamline interfaces, target integration, external supports, and installation envelopes remain deployment-specific.

The external-detector implementations in `afterSRC/` and `infrontofSamuraiMag/`, or their repository-preserved locations, are legacy/reference routes. They shall remain independently testable and shall not be modified, deleted, or silently promoted into this baseline.

Compatibility labels containing `CompactOne` and the directory `compactInVacuum/` may remain in executable paths. The instrument names above are authoritative.

## 2. Decision and evidence states

Engineering selections use:

- `FROZEN`: approved project requirement.
- `PROVISIONAL`: current integration value requiring evidence.
- `RECOMMENDED`: preferred prototype candidate; alternatives remain open.
- `PLACEHOLDER`: architecture-only value that fails an applicable strict gate.
- `PURCHASED-PART-CONTRACT`: governed by a supplier or certified drawing.

Unknown quantities remain `TBD` or unresolved. Exact-looking dimensions shall not be invented.

Deployment interface claims use:

- `A — EXTERNAL CONSTRAINT`
- `B — LEGACY INHERITANCE`
- `C — ENGINEERING ASSUMPTION`
- `D — UNRESOLVED / TBD`

## 3. Frozen common-platform requirements

- Four sectors: LEFT, RIGHT, UP, DOWN.
- Three channels per sector: deuteron, small-angle proton, large-angle proton.
- Twelve active detectors total.
- Detector axes point toward the target center.
- Configured radii refer to active-plastic centers.
- One nominal 50-ohm signal path per detector; bias may share the coax through external bias tees.
- Active amplifiers, bias tees, and digitizers remain outside vacuum by default.
- One removable three-detector holder per sector.
- Full target-region-to-complete-active-disc acceptance is preserved.
- Coincidence geometry and per-channel active-acceptance metrics are exported.
- Physical CAD is separated from keepouts, datums, service centerlines, and physics overlays.
- Both baseline deployments generate independently.
- Preserved external routes remain unchanged and independently regressible.

## 4. Temperature-monitoring disposition

A dedicated temperature-monitoring or thermometer-style subsystem is not a platform requirement.

The common platform shall not contain or require:

- a physical `TemperatureSensor`;
- per-detector temperature channels;
- temperature harnesses or centerlines;
- wires-per-temperature-channel capacity;
- a housekeeping feedthrough;
- a housekeeping capacity gate;
- a resolved temperature-sensor supplier model;
- temperature manifests or generated metrics.

These elements shall be removed rather than hidden. Schema version 3 rejects their former configuration keys with a migration error.

An optional deployment-level spare auxiliary interface may be introduced in a future revision only if justified. It shall default to disabled, create no physical feedthrough or cable when disabled, use neither “temperature” nor “housekeeping” terminology, and remain outside required validation.

## 5. Detector-head prototype

The semantic axial stack is:

1. fast plastic scintillator;
2. thin reflector/light-treatment envelope;
3. optical coupling layer;
4. SiPM package;
5. minimal sensor PCB or metallic carrier;
6. shallow light-tight rear mounting face;
7. short cable exit.

The recommended starting prototype is:

| Component | Default value | Status |
|---|---:|---|
| active plastic diameter | 20.0 mm | recommended |
| active plastic thickness | 5.5 mm | recommended within 5–6 mm |
| reflector radial envelope | 0.25 mm | placeholder material |
| optical coupling thickness | 0.50 mm | provisional |
| SiPM package depth | 1.50 mm | recommended candidate envelope |
| sensor PCB/carrier depth | 1.20 mm | provisional |
| rear internal clearance | 0.00 mm | provisional |
| rear mounting-face thickness | 1.00 mm | provisional |
| SiPM candidate | NDL EQR15 11-6060D-S | recommended |
| SiPM active class | approximately 6 × 6 mm | recommended |

The default physical housing depth is calculated, not independently specified:

`5.50 + 0.50 + 1.50 + 1.20 + 0.00 + 1.00 = 9.70 mm`

The physical-depth gate is 18.0 mm maximum from active entrance face to rear physical housing. The 3.0 mm short cable exit and the 20.0 mm connector keepout are reported separately and do not increase this metric.

The reflector envelope surrounds the active plastic without covering its complete entrance face. The coupling contacts the active rear readout region. The SiPM is centered directly behind the coupling. The carrier contacts the SiPM and rear mounting face, providing a real passive conductive path without an artificial long thermal bridge.

The light-tight housing is a shallow sleeve and rear face. It shall not recreate the former 35 mm nose plus 44 mm rectangular package. Semiconductor microstructure and detailed connector internals are out of scope.

The rear mounting face provides the insertion stop and mounting datum. A D-flat and matching nest land provide anti-rotation without protruding into a neighboring acceptance cone. Detector removal is axial and rearward after clamp release. The default sampled withdrawal distance is 12.0 mm, sufficient to clear the 3.0 mm nest.

The carrier, cable exit, connector, reflector selection, and detailed PCB remain provisional until drawings or prototype measurements resolve them.

## 6. Sector holder

Each sector uses one coherent fabricated or machined carrier containing exactly:

- one deuteron detector head;
- one small-angle proton detector head;
- one large-angle proton detector head.

The holder comprises:

- one connected carrier plate with three machined acceptance windows;
- three rear cylindrical nest cradles;
- three insertion stops at the detector rear faces;
- three D-flat anti-rotation lands;
- three removable clamp bridges;
- two simplified M3-class fastener envelopes per clamp;
- one rear cable-routing lane;
- one common chamber-interface block;
- one primary plane, one round locating pin, and one clocking slot;
- three survey datums.

M3 and locating-pin geometry demonstrates assembly access only. Fastener selection remains provisional and shall not be called fabrication-ready.

Detector heads are inserted axially from the rear, stopped on the rear mounting face, clocked by the D-flat, and retained by the removable bridge. Clamp fasteners are accessed from the rear. Releasing one bridge permits removal of one head without removing the other two.

The whole sector is located by a plane–pin–slot interface and extracted radially outward. Five exact solid poses sample the straight 70 mm extraction path. The displayed removal overlay is diagnostic only; collision validation uses the exact sampled holder solids.

The plate, nests, clamps, and fastener envelopes shall clear every complete active-acceptance cone. The plate includes a common rear service-lane relief. Arbitrary per-detector wall rails, wall anchors, cylindrical thermal straps, and a synthesized wall backbone are prohibited.

The holder is a provisional manufacturable concept, not a released drawing. Tool access, chamber closure, pin retention, tolerances, surface finish, and production fasteners remain to be resolved.

## 7. Physical and overlay roles

Every generated object has one engineering role:

- `physical`
- `purchased_component_interface`
- `keepout`
- `datum`
- `service_centerline`
- `physics_acceptance`
- `optional_reference_geometry`

Default visibility is:

| Role | Default |
|---|---|
| physical | visible |
| purchased component/interface | visible |
| keepout | hidden |
| datum | hidden |
| service centerline | hidden |
| physics acceptance | hidden |
| optional reference geometry | hidden |

Generated documents use meaningful groups including `DetectorHead`, `SectorHolder`, `Target`, `Services`, `Chamber`, `Keepouts`, `Datums`, `PhysicsAcceptance`, and `OptionalReference` where applicable.

Material-based colors and transparency support inspection but are not geometry requirements. The active plastic, optical coupling, SiPM, PCB/carrier, housing, and holder shall remain visually distinguishable.

## 8. Services and passive thermal path

- Twelve signal channels are required.
- Four sector-grouped signal feedthrough interfaces provide sixteen provisional slots.
- One protective/equipotential bond per sector is required.
- Signal shields are not the sole protective-earth path.
- Cable routes, connector keepouts, bend envelopes, and centerlines are nonphysical overlays unless explicitly classified otherwise.
- No dedicated temperature or housekeeping feedthrough is generated.

The conductive path contract is:

`SiPM package -> sensor PCB/carrier -> rear mounting face -> detector nest -> sector carrier plate -> chamber mounting interface`

The path represents contact connectivity. It is not thermal FEA and shall not be satisfied by adding a fictitious long bridge.

## 9. Physics geometry

The repository values remain:

| Channel | Repository value | Previously supplied nominal | Disposition |
|---|---:|---:|---|
| proton large | 53.4° | approximately 55.9° | unresolved; do not change without evidence |
| proton small | 11.2° | approximately 11.3° | unresolved; do not change without evidence |

This mechanical redesign does not resolve the discrepancy. Active-center radii and directions remain unchanged.

Validation exports active-center angle/radius, active-face radius, angular extent, approximate solid angle, and eight configured coincidence pair metrics. It does not claim detector-response or Geant4 fidelity.

## 10. Acceptance and collision validation

The complete ruled volume from the active target region to each complete active disc is checked against:

- target hardware;
- every other detector head;
- carrier plates, nests, clamps, and interface blocks;
- simplified purchased fastener envelopes;
- cable and connector keepouts;
- service hardware;
- chamber hardware.

Validation also requires:

- twelve non-null, valid detector-head solids;
- no detector-head overlap;
- four non-overlapping three-head sector assemblies;
- clear detector withdrawal after clamp release;
- clear sampled radial sector removal;
- clear target motion sweep;
- clear signal routing;
- a closed vacuum control volume;
- all internal physical parts inside the selected chamber;
- connected passive thermal paths.

## 11. Deployment profiles

### 11.1 CompactInVacuum-afterSRC

- Baseline instrument downstream of SRC.
- Selected screening chamber: cylindrical 440 mm internal diameter, provisional.
- Front/rear ICF114 values are legacy/provisional evidence, not approved site requirements.
- Available envelope, service-removal closure, purchased interface drawings, support datum, and pressure-vessel release remain unresolved.
- The preserved external afterSRC route remains a legacy fallback/reference.

### 11.2 CompactInVacuum-preSAMURAI

- Baseline instrument upstream of the SAMURAI terminal.
- Selected screening chamber: square 450 × 450 mm internal section, provisional.
- VF100/VG80 evidence inherited from external work is not automatically authoritative for the compact deployment.
- Available envelope, mating-chain ownership, service-removal closure, purchased interface drawings, support datum, and pressure-vessel release remain unresolved.
- The preserved external SAMURAI-front route remains reference engineering work.

## 12. Strict-validation semantics

Non-strict mode permits explicit warnings for unresolved supplier, material, site-envelope, chamber-access, and pressure-vessel evidence. Geometry, capacity, acceptance, collision, and schema failures remain fatal.

Strict mode converts applicable evidence warnings to failures. Strict validation shall not fail because a removed temperature sensor, temperature harness, housekeeping channel, or housekeeping feedthrough is absent.

Current legitimate strict gates include:

- reflector/optical and SiPM supplier evidence;
- carrier/PCB definition;
- purchased beam and signal-interface drawings;
- vacuum material and cleaning evidence;
- chamber external-pressure/buckling FEA;
- site envelopes;
- resolved sector-removal access closure.

## 13. Schema migration

CompactInVacuum schema version 3 replaces:

- `detector.cassette` with `detector.head`;
- `sector_cartridge` with `sector_holder`;
- arbitrary outer detector length with calculated stack depth;
- protruding `anti_rotation_tab_mm` with `anti_rotation_flat_depth_mm`.

Schema version 3 rejects all former temperature and housekeeping fields. They are not ignored and no compatibility geometry is created. Deployment service-port roles are limited to `rotary` and `signal`.

Legacy schema-1 compatibility profiles remain loadable for the preserved old entry point, but their dedicated housekeeping block has also been removed.

## 14. Required artifacts

The redesign shall generate:

- isolated detector head: FCStd, STEP, geometry metrics JSON, PNG;
- transparent/exploded detector head: FCStd, STEP, geometry metrics JSON, PNG;
- three-channel sector holder: FCStd, STEP, geometry metrics JSON, PNG;
- four-sector internal assembly: FCStd, STEP, geometry metrics JSON, validation JSON, PNG;
- CompactInVacuum-afterSRC: FCStd, STEP, geometry metrics JSON, validation JSON, PNG;
- CompactInVacuum-preSAMURAI: FCStd, STEP, geometry metrics JSON, validation JSON, PNG;
- before/after comparisons for detector side, sector, and internal assembly;
- separate diagnostic renders with keepouts and acceptance volumes visible.

Runtime state, caches, and machine-specific files remain untracked.

## 15. Evidence still required

- Approved afterSRC and pre-SAMURAI site envelopes and interface drawings.
- Certified purchased beam-interface and signal-feedthrough drawings.
- Resolved PCB/carrier, connector, cable, strain-relief, reflector, and optical-pad choices.
- Prototype optical collection, timing, uniformity, saturation, and vacuum/bake testing.
- Sector-holder tolerances, tool access, pin retention, fasteners, finish, and fabrication drawings.
- Chamber access closure and sector extraction demonstration.
- Vacuum material/cleaning qualification.
- Chamber external-pressure, weld, support, transport, and seismic/load analysis as applicable.
- Evidence resolving 53.4° versus approximately 55.9°, and 11.2° versus approximately 11.3°.

## 16. Change history

- 2026-07-27 v1.0: established a common CompactInVacuum platform with two baseline deployments.
- 2026-07-29 v2.0: removed temperature monitoring end-to-end; replaced the long cassette with a 9.70 mm calculated detector head; replaced arbitrary rails with one coherent sector carrier; added engineering display roles, removal validation, and schema-v3 migration.
