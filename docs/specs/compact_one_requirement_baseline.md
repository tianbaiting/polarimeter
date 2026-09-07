# CompactInVacuum Requirement Baseline v2.7

## 1. Authority and scope

This document is the requirement authority for the common CompactInVacuum detector platform and its two baseline deployments:

1. `CompactInVacuum-afterSRC`, downstream of SRC.
2. `CompactInVacuum-preSAMURAI`, upstream of the SAMURAI terminal.

Both deployments place the compact plastic-scintillator detector heads, SiPM packages, passive internal services, and sector holders inside vacuum. Detector technology and common mechanical architecture are shared. Chamber geometry, purchased beamline interfaces, target integration, external supports, and installation envelopes remain deployment-specific.

The external-detector implementations in `external_version/afterSRC/` and
`external_version/infrontofSamuraiMag/` are legacy/reference routes. They shall remain independently
testable and shall not be modified, deleted, or silently promoted into this baseline.

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

The active deployments use four detailed boxed carriers with two relieved cheeks, front/rear crossmembers, three rear nests and removable clamps, three routed passive coax connections, and one radial plane–pin–slot dock per sector. A common annular support near z=140 mm transfers load to the permanent side and bottom walls. The former rear C-frame is retained only as a comparison configuration.

A removable downstream retaining bridge clamps each dock with two axial screw envelopes. The bridge, screws, locating pins and coax/ground interfaces are represented for every sector. A rear-facing cylindrical handling journal projects behind each carrier; its capture tool remains vertical in the chamber coordinate system.

The specified service sequence is UP, RIGHT, LEFT, DOWN; installation reverses this sequence. It supersedes the former independent-removal design target for this prototype. Each module disengages radially inward, translates downstream, turns about its handling journal if needed, centers under the ICF305 port, and lifts upward. Other sectors remain physical obstacles until their preceding removal step is complete. Validation must distinguish loaded-module/capture-tool transport from connection release, retaining-bridge access, and purchased capture mechanism qualification. A clear transport path alone shall not be called a complete maintenance-process certificate.

The cheeks, crossmembers, nests, clamps, and fastener envelopes shall clear every complete active-acceptance cone. The crossmembers include the declared cable and handling-journal reliefs. Arbitrary per-detector wall rails, wall anchors, cylindrical thermal straps, and a synthesized wall backbone are prohibited.

The holder is a provisional manufacturable concept, not a released drawing. Tool access, chamber closure, pin retention, tolerances, surface finish, and production fasteners remain to be resolved.

Every removable sector-holder structural interface shall contact either a permanent chamber wall or a separately defined stationary load-bearing pad/pedestal with zero geometric gap. Every stationary pad/pedestal shall in turn contact a permanent chamber wall, or the explicitly defined common stationary support frame, with zero gap. The common frame shall contact permanent side/bottom walls with zero gap. A protective-ground strap is electrical bonding only and shall never be used to bridge a structural mounting gap or satisfy the load path.

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
- Each protective bond shall have nonzero physical length and contact both the removable holder/block and the stationary support/permanent chamber. A zero-length marker, virtual datum, locating pin, or coax shield does not satisfy this requirement.
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
- clear sampled configured holder-release poses, without treating them as proof of complete extraction;
- clear target motion sweep;
- clear signal routing;
- a closed vacuum control volume;
- all internal physical parts inside the selected chamber;
- connected passive thermal paths.
- zero-gap removable-holder-to-stationary-support and stationary-support-to-permanent-wall structural paths;
- no detector support, locating pin, ground bond, or permanent support inside the removable access-closure lift corridor.

## 11. Deployment profiles

### 11.1 CompactInVacuum-afterSRC

- Baseline instrument downstream of SRC.
- Selected screening chamber: square 440 × 440 mm internal section, provisional. The active ICF305 maintenance-access integration study length is 420 mm with the upstream outer face retained at `z=-50 mm`; the former 360 mm body remains the ICF253 comparison envelope and is not silently treated as the active access-port design.
- A cylindrical afterSRC chamber is not part of the selected CompactInVacuum-afterSRC profile.
- Front/rear ICF114 values are legacy/provisional evidence, not approved site requirements.
- The maintenance opening is a top-wall circular ICF port with a removable ICF blank flange. Elastomer/O-ring sealing is prohibited for this deployment; the screening seal is an oxygen-free-copper metal gasket. The maximum allowable helium leak rate is `1.0e-10 Pa m^3/s`, based on the user-supplied Toshiba inspection sheet; document identity and applicability to the complete compact chamber remain to be closed before fabrication release.
- The access-port comparison family is `ICF253`, `ICF305`, and `ICF356`. Vendor-catalog screening dimensions distinguish the flange hole from the applicable pipe outside diameter: ICF253 uses a `198.5 mm` flange bore / `203 mm` pipe OD, ICF305 uses `251.0 mm` / `254 mm`, and ICF356 uses `301.8 mm` / `305 mm`. ICF305 is the active recommended prototype; ICF253 remains a smaller-port comparison requiring reorientation; its former side-wall UP-holder rejection is historical and shall not be applied unchanged to the new common-frame carrier, and ICF356 remains the enlarged-envelope comparison.
- A top access flange alone does not close the sector-removal requirement. Validation shall separately report: flange-to-chamber fit, flange-to-service-port clearance, detached-holder passage screening, and the complete installed-holder release/reorientation/lift path. The existing straight `70 mm` radial release path shall not be re-labelled as a successful top-port extraction path.
- The removable ICF fixed/blank closure owns no detector support, locating datum, structural fastener, thermal sink, protective-ground termination, cable clamp, or target-mechanism load. Removing the blank flange shall leave all internal detector supports positioned on permanent chamber structure.
- Both compact deployments use the boxed carriers and annular support defined above, four radial sector docks, and deployment-specific permanent-wall feet. This supersedes the former afterSRC UP `-X` pedestal at `y=180 mm`.
- Available envelope, the complete service-removal motion, purchased ICF305 interface drawing, support datum, and pressure-vessel release remain unresolved.
- The preserved external afterSRC route remains a legacy fallback/reference.

### 11.2 CompactInVacuum-preSAMURAI

- Baseline instrument upstream of the SAMURAI terminal.
- Selected screening chamber: square 450 × 450 mm internal section, provisional; the ICF305 top-access prototype uses a 420 mm body with upstream outer face at `z=-50 mm`. The former 380 mm service-plate chamber remains a comparison candidate.
- The top maintenance opening adopts the same provisional ICF305 geometry and load-free closure as afterSRC; supplier, seal/site applicability, and complete extraction evidence remain unresolved. Signal services occupy the permanent upstream top strip outside the maintenance flange.
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
- afterSRC maintenance-port metal-seal evidence, helium-leak acceptance, flange/service clearances, and complete extraction motion.

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

- 2026-09-07 v2.7: promoted four detailed boxed modules to both canonical deployments, with a permanent annulus, downstream retaining bridges, rear handling journals, complete installed/parked signal looms and the UP/RIGHT/LEFT/DOWN service sequence. Loaded-module and modeled capture/bridge motion remain distinct from full service-tool and fabrication qualification.

- 2026-09-06 v2.6: authorized one detailed RIGHT-sector boxed-carrier study on a near-detector annular support, with connector disconnection, tool access and complete controlled extraction. This is an isolated design study, not replacement of either canonical deployment.
- 2026-09-06 v2.5: selected the common rear open C-frame, four axial-release sector docks, and top ICF305 access for both compact prototypes; retained independent complete extraction as an unresolved design target.

- 2026-09-01 v2.4: clarified that sampled holder-release poses do not constitute proof of the
  complete extraction path; aligned downstream documentation and validation terminology with the
  ICF305 fixed-wall support design.
- 2026-07-27 v1.0: established a common CompactInVacuum platform with two baseline deployments.
- 2026-07-29 v2.0: removed temperature monitoring end-to-end; replaced the long cassette with a 9.70 mm calculated detector head; replaced arbitrary rails with one coherent sector carrier; added engineering display roles, removal validation, and schema-v3 migration.
- 2026-07-29 v2.1: selected the square 440 × 440 mm screening chamber for CompactInVacuum-afterSRC and removed its cylindrical chamber candidate.
- 2026-08-30 v2.2: froze the afterSRC maintenance opening as an all-metal top ICF port with an oxygen-free-copper gasket and `1.0e-10 Pa m^3/s` helium-leak criterion; added ICF253/305/356 comparison candidates, selected ICF305 for the active prototype, and kept complete sector extraction as an independently validated unresolved motion.
- 2026-08-30 v2.3: prohibited all detector support/datum/ground ownership on the removable ICF closure; required zero-gap removable-holder-to-stationary-pad-to-permanent-wall load paths; and moved the afterSRC UP-sector mount from the opened `+Y` wall to a stationary `-X` side-wall pedestal while keeping the long wall-reaching member out of the removable holder.

## 17. Boxed-sector design study

The registered `compactBoxedSectorStudy` first develops one complete RIGHT sector using the unchanged three active detector positions and the afterSRC ICF305 chamber. Its candidate carrier uses two side cheeks, three nests, local crossmembers, a plane-pin-slot docking foot and an accessible draw screw. A fixed annular support near the large-angle detector transfers load to permanent side/bottom walls. The ring is retained during routine detector maintenance; segmentation and fabrication release are separate decisions.

The study must include real detector-head solids, retention and docking interfaces, three passive pigtails and their disconnect envelopes, protective bonding, a defined grasping joint and the handling-tool envelope. The other three sectors are reserved by conservative module envelopes, supplemented by their actual detector-head solids. Results shall explicitly identify this single-sector scope.

Maintenance is performed with the blank flange and gasket removed. Connector plugs are withdrawn and parked before the module moves. A capture tool supports the module before its draw screw is removed. The module releases inward, translates downstream, turns on a controlled joint whose axis is parallel to beam Z, centers below the opening and lifts out. The handling rod stays vertical. This refines the conceptual beam-axis turn into an executable tool-controlled motion.

Check the complete modeled motion against permanent support, chamber, flange, services and the three reserved sectors. Discrete clear poses alone do not prove motion clearance: use analytic swept envelopes or interval certificates based on minimum shape distance and an upper bound on point displacement. Any collision or interval left uncertified shall fail the motion gate. Intended mating contacts require explicit geometric certificates; they cannot be bypassed by blanket obstacle exclusions. The full aperture is retained; do not shrink an arbitrary keepout to make a mechanism pass.

Transport dimensions, microcoax bend radius, connector/capture-tool envelopes and fabrication details are provisional. Geometry certification applies only to those modeled envelopes. Supplier/material qualification, stiffness, clamp preload, human reach/handling forces and available external headroom remain strict evidence gates. No manufacturing release or four-sector detailed-assembly claim follows from this study.

## 18. Complete boxed deployment integration

Both canonical deployments shall export all four detailed carriers, twelve complete detector heads, four locating-pin pairs and retaining bridges, twelve installed signal looms, four ground bonds, the common permanent annular support, the selected chamber, target and deployment-specific beamline interfaces. Neighbor reservation boxes are not a substitute for any of the four physical modules.

The common dimensional source is `compactInVacuum/config/common_boxed.yaml`. Sector placement, removal order, rear handling journal, axial retaining bridges and service-parking coordinates are provisional integration parameters there. The upper-sector parking fixture attaches to the permanent left wall, clear of the top opening. The rear journal and tool provide a path behind the three loaded detector heads, especially for the final DOWN removal. A separate maintenance-open document and extraction poses supplement each closed canonical assembly. The original single-RIGHT-sector study remains a reproducible comparison and does not certify the complete deployments.

All strict evidence gates in section 12 apply to the new canonical engine, including beam/signal/access supplier drawings, materials and optical components, chamber pressure integrity, site/overhead envelope, fastener and capture-mechanism detail, and physical service handling. Geometry failures remain fatal; unresolved evidence remains explicitly non-strict prototype-only.

The full-deployment inward staging travel is 40 mm before the 96 mm downstream transfer. This reduces the rear handling-rod offset to 30 mm, keeping the complete vertical rod inside the circular opening during transfer. It replaces the single-sector study's 14 mm initial release for the full deployment; detector operating positions remain unchanged.

Each retaining bridge first disengages downstream by 20 mm, steps radially outward by 20 mm to clear the rear crossmember, steps 26 mm tangentially away from the engaged handling rod, transfers another 40 mm downstream, centers below the opening and lifts out. The loose bridge and fastener solids are included in the trajectory checks; the actuating/holding tool remains a purchased-mechanism qualification item.
