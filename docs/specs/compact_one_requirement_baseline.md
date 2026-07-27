# CompactInVacuum Requirement Baseline v1

## 1. Authority and scope

This document is the requirement authority for the common CompactInVacuum detector platform and its two baseline instruments:

1. `CompactInVacuum-afterSRC`, installed downstream of SRC.
2. `CompactInVacuum-preSAMURAI`, installed before the SAMURAI terminal.

Both instruments place the scintillators, SiPM packages, local passive services, and detector supports inside vacuum. They share detector technology and engineering philosophy, but their chamber geometry, beamline interfaces, target integration, supports, and maintenance envelopes are site-specific.

The previously developed afterSRC external-detector configuration in `afterSRC/` is retained as a legacy/fallback/reference route. It is not one of the two baseline instruments. The external-route mechanical baseline remains in `docs/specs/BLP_v1_requirement_baseline.md`; values from that baseline shall not become CompactInVacuum site requirements without independent evidence.

| Item | afterSRC compact | pre-SAMURAI compact | legacy afterSRC external |
|---|---|---|---|
| Baseline status | baseline | baseline | legacy/fallback |
| Detector location | in vacuum | in vacuum | outside vacuum |
| Detector platform | common CompactInVacuum platform | common CompactInVacuum platform | established external design |
| Chamber geometry | site-specific / TBD | site-specific / TBD | existing reference geometry |
| Beam interfaces | verify independently | verify independently | existing legacy assumptions |

```text
SRC
 |
 +-- CompactInVacuum-afterSRC
 |
 |   beam transport
 |
 +-- CompactInVacuum-preSAMURAI
 |
SAMURAI

Both compact instruments:
  common detector platform
  site-specific mechanics and interfaces

Legacy:
  afterSRC external-detector design
  reference/fallback only
```

Repository compatibility names such as `CompactOne-afterSRC`, `CompactOne-infrontSamurai`, and the directory `compactInVacuum/` may remain until a controlled API/path migration is justified.

### 1.1 Requirement levels

Requirements shall be recorded at exactly one of these levels:

- **COMMON PLATFORM REQUIREMENTS:** scintillator and SiPM technology, optical package, cassette, sector cartridge, detector services, electronics, calibration, thermal-path semantics, and common physics/response studies.
- **AFTER-SRC SITE REQUIREMENTS:** actual available envelope, usable beam aperture, neighboring equipment, flange interfaces, support/alignment, target integration, and installation/maintenance access downstream of SRC.
- **PRE-SAMURAI SITE REQUIREMENTS:** the same site categories, independently established for the location before the SAMURAI terminal.

Unknown site quantities shall be `TBD` and shall name the drawing, survey, measurement, or beamline-owner decision needed to close them.

## 2. Decision-state vocabulary

Every engineering selection that can affect procurement or validation shall carry one of these states:

- `FROZEN`: approved project requirement; change requires baseline revision.
- `PROVISIONAL`: current engineering value used for integration; evidence is still required.
- `RECOMMENDED`: preferred prototype candidate from study or report; alternatives remain allowed.
- `PLACEHOLDER`: permits architecture/code development only and must fail an applicable strict gate.
- `PURCHASED-PART-CONTRACT`: geometry and acceptance are governed by a supplier/certified drawing. Missing mandatory drawing data shall be explicit.

Unknown values shall remain unresolved. Exact-looking dimensions shall not be invented.

## 3. Frozen platform requirements

- Four sectors: LEFT, RIGHT, UP, DOWN.
- Three physics channels per sector: D, P-small, P-large.
- Total detector count: twelve.
- CompactOne detectors, SiPMs, minimum passive services, and sector supports are inside vacuum.
- Active electronics, bias tees, amplifiers, and digitizers remain outside vacuum by default.
- One separately testable nominal 50-ohm coax signal path per detector; SiPM bias shares that coax through an external bias tee.
- Temperature/housekeeping monitoring and spare service capacity are required.
- Development hierarchy: single detector -> golden cassette -> golden three-channel sector -> four-sector polarimeter.
- Legacy external-route code and evidence remain preserved and independently testable, without being promoted into the two-instrument baseline.

## 4. Recommended prototype detector platform

These values are recommendations, not frozen production requirements:

- Active medium: fast blue plastic scintillator.
- Active diameter: approximately 20 mm for the compact prototype geometry.
- First prototype active-thickness band: 5–6 mm, with the configuration able to represent other tested thicknesses.
- SiPM baseline: NDL EQR15 11-6060D-S.
- SiPM class: approximately 6 × 6 mm active area.
- Measured total optical collection target: 2–5%. This is a system-level measurement target, not a supplier specification.

The software shall keep the active plastic, optical package, SiPM, and cassette mechanical envelope independent.

## 5. Detector cassette

Every detector channel shall expose engineering-envelope representations for:

- active plastic;
- optical coupling region;
- reflector/light-treatment envelope;
- SiPM;
- removable sensor carrier;
- thermal spreader/path;
- light-tight shell;
- mounting datum;
- anti-rotation feature;
- insertion stop;
- detector-side cable strain relief;
- cable/connector keep-out;
- optional temperature sensor.

The cassette shall be independently generated and validated. Microscopic conductor and semiconductor detail is out of scope.

## 6. Sector cartridge

The preferred internal structure is four removable sector cartridges. Each cartridge shall:

- carry D, P-small, and P-large cassettes;
- define common mounting and survey datums;
- provide a shared thermal path;
- provide service routing and strain relief;
- provide a chamber/service-structure interface;
- have an explicit removal/service envelope;
- preserve the full active acceptance of all three detectors.

The former twelve-arm support is a legacy scaffold, not the preferred architecture.

## 7. Target subsystem

The target subsystem shall represent:

- target foil and active target region;
- removable frame/holder;
- rotary arm, hub, shaft, and feedthrough interface;
- WORK and PARK states;
- mechanical hard stops;
- target-center datum;
- complete motion sweep between WORK and PARK.

The motion sweep shall be checked against beam stay-clear, all cassettes, cartridges, cables, connector keep-outs, feedthrough/manifold structures, and chamber structures.

## 8. Electrical, grounding, and thermal services

- Fast signal channels: 12 minimum.
- Nominal impedance: 50 ohm.
- Bias architecture: signal-coax sharing with external bias tees.
- Active in-vacuum electronics: disabled by default.
- Temperature channels: one optional sensor per cassette, with capacity for all twelve baseline cassettes.
- Grounding: a dedicated protective/equipotential bond is required; signal shields shall not be the sole protective-earth path.
- Spare capacity: at least one fast-signal spare per sector is recommended until feedthrough procurement is frozen.
- CAD shall include feedthrough/manifold envelopes, coax route envelopes, connector keep-outs, and strain-relief locations.

The thermal conduction intent shall be:

`SiPM -> sensor carrier/copper spreader -> cassette -> sector cartridge -> chamber/service structure`

Strict validation shall distinguish a declared, connected path from a floating or unresolved path. Full thermal FEA is a later gate.

## 9. Materials

Components relevant to accepted particle paths shall support:

- material name;
- density when known;
- vacuum-compatibility status;
- physics-sensitive flag;
- purchased/project-designed classification.

Validation shall produce a nominal path-material inventory. The intended accepted path is approximately target -> vacuum -> active plastic. Structural material in that path is a failure unless explicitly reviewed.

## 10. Chamber candidates

Both square and cylindrical cross-sections are valid engineering candidates.

The preferred concept to evaluate is a short cylindrical external-pressure shell with a removable flat service plate/manifold and four internal sector cartridges. This is not yet a frozen fabrication choice.

Every candidate shall report:

- internal envelope;
- shell material volume;
- approximate mass using declared density;
- service accessibility;
- cartridge clearance and removal envelope;
- target-motion clearance.

CAD wall thickness is a screening input only. Fabrication thickness requires a later external-pressure/buckling FEA and weld-detail gate.

## 11. Purchased vacuum interfaces

Standard ICF/CF and JIS hardware shall be represented as purchased components governed by certified drawings. The configuration shall separate:

- purchased standard component;
- project-designed welded transition/stub;
- project-designed chamber or service plate.

Purchased interfaces shall support standard, supplier, part number, certified drawing reference, nominal clear bore, mating envelope, knife-edge protected zone, weld interface, and decision status.

The current 63.6 mm OD / 63.0 mm ID tube has a 0.30 mm radial wall. It is a non-fabricable placeholder and shall fail strict engineering validation.

Interface statements shall carry one evidence class:

- `A — EXTERNAL CONSTRAINT`: supported by an approved beamline/interface requirement, signed drawing, or responsible-owner decision.
- `B — LEGACY INHERITANCE`: inherited from an external-detector or earlier design and not independently established for a compact instrument.
- `C — ENGINEERING ASSUMPTION`: used for screening or integration studies, but not an external requirement.
- `D — UNRESOLVED / TBD`: no justified selection exists yet.

Class `B` or `C` shall never be described as class `A`. A purchased-part contract may only become site-authoritative after the mating interface and certified drawing are both resolved.

## 12. Deployment profiles

### 12.1 CompactInVacuum-afterSRC

- Location: after SRC.
- Baseline status: current baseline compact instrument.
- Detectors: inside vacuum, using the common CompactInVacuum platform.
- Beamline mating interfaces: `D — UNRESOLVED / TBD`. Front/rear ICF114 values in the old afterSRC design are `B — LEGACY INHERITANCE`, not independently supported CompactInVacuum requirements.
- Target rotary mounting interface: current ICF70 envelope is `C — ENGINEERING ASSUMPTION`; the actual site constraint, purchased rotary model, load case, and signed outline drawing are unresolved.
- Chamber dimensions, detector radii, port layout, actual clear bore, transition/stub geometry, bellows/adapters, available envelope, pump/gauge requirements, external service envelope, support/alignment, and maintenance access are site-specific and remain TBD unless separately supported.
- Closure evidence: approved afterSRC beamline interface drawing, local XYZ survey/envelope, neighboring-equipment model, beam-stay-clear definition, vacuum-services ownership, support datum definition, and installation/maintenance review.
- Legacy route: `afterSRC/` remains available only as a legacy/fallback/reference alternative.

### 12.2 CompactInVacuum-preSAMURAI

- Location: upstream of the SAMURAI terminal.
- Baseline status: current baseline compact instrument.
- Detectors: inside vacuum, using the common CompactInVacuum platform.
- Beamline mating interfaces: `D — UNRESOLVED / TBD`.
- Existing external-route evidence identifying a VF100 gate-valve boundary and an upstream VF100/downstream VG80 profile is `B — LEGACY INHERITANCE` until the compact instrument's actual mating chain and ownership are confirmed.
- CompactOne shall not silently inherit a complete chamber from the external route.
- Exact mating-chain ownership, usable bore, available XYZ envelope, straight length, pump/gauge requirements, target-feedthrough interface, support/alignment envelope, and service-removal envelope remain unresolved until beamline confirmation.
- Closure evidence: approved pre-SAMURAI interface drawing, local survey/envelope, neighboring-equipment model, beam-stay-clear definition, vacuum-services ownership, support datum definition, and installation/maintenance review.

Deployment profiles shall contain only site-specific constraints. Detector, cassette, cartridge, cabling philosophy, electronics interface, and calibration semantics shall remain common where feasible.

## 13. Physics geometry and acceptance

For every active detector face, export:

- center theta and phi;
- active diameter and thickness;
- active-center radius;
- theta minimum and maximum;
- azimuth coverage where meaningful;
- approximate solid angle.

For D/P-small/P-large coincidence combinations, export geometry-level acceptance-overlap descriptors without claiming detector-response or Geant4 fidelity.

The same resolved configuration and geometry metrics shall be consumable by future Geant4 construction.

## 14. Full-path LOS

The full cone from the active target region to the complete active detector disc shall be checked against:

- target frame, arm, hub, and shaft;
- other cassettes;
- sector cartridge material;
- cables and connector keep-outs;
- service/manifold structures;
- chamber structures.

Failures shall identify channel, sector, obstructing component, intersection volume or minimum margin, and material metadata. Internal components shall not be silently whitelisted.

## 15. Validation categories and strict semantics

Reports shall group checks under:

- `physics`
- `beamline`
- `detector`
- `sector_cartridge`
- `target`
- `los`
- `services`
- `vacuum`
- `mechanical`
- `thermal`

Non-strict mode may carry explicit warnings for unresolved supplier part numbers, prototype material choices, reflector choice, and temperature-sensor model.

Strict mode shall fail for:

- impossible structural tube/wall geometry;
- conflated or absent active/cassette geometry;
- incomplete target mechanism or colliding motion sweep;
- insufficient signal or housekeeping capacity;
- blocked full-acceptance LOS;
- unresolved beam-aperture incompatibility;
- invalid vacuum boundary;
- missing cassette/cartridge mounting or removal semantics;
- missing thermal conduction path.

Strict mode shall not be a cosmetic exit-code flag.

## 16. Required artifacts and stable comparison metrics

Reproducible outputs shall include, where practical:

- one detector cassette: FCStd, STEP, JSON;
- one golden sector cartridge: FCStd, STEP, JSON;
- four-sector internal assembly: FCStd, STEP, JSON;
- CompactOne-afterSRC assembly: FCStd, STEP, JSON;
- CompactOne-infrontSamurai assembly: FCStd, STEP, JSON.

Cross-machine comparison shall use stable quantities: solid counts, bounding boxes, material volumes, detector centers/angles, target states/sweep, service capacities, and validation values. Byte-identical CAD files are not required.

## 17. Gates still requiring physical evidence

- Signed purchased ICF/JIS component drawings and usable bores.
- afterSRC and SAMURAI available installation envelopes and service-removal clearances.
- Rotary-feedthrough load, torque, backlash, life, bake temperature, and outline.
- Vacuum coax/feedthrough part numbers, installed bandwidth, connector gender, cable bend radius, and bake rating.
- Prototype optical collection, uniformity, timing, SiPM saturation, temperature coefficient, and batch variation.
- Vacuum material qualification and populated-detector bake limit.
- Chamber external-pressure/buckling FEA, weld design, support loads, and transport loads.
- Geant4 acceptance/background study using the authoritative CompactOne geometry.

## 18. Change history

- 2026-07-27 v1.0: established CompactOne as a shared in-vacuum platform with afterSRC and in-front-of-SAMURAI deployment profiles while preserving both external routes.
