# CompactOne Architecture Audit

## Audit scope

Audit date: 2026-07-27  
Repository: `tianbaiting/polarimeter`  
Audit baseline: commit `679849a200591a4bcce76db62c6572ba656525e8`

The repository contains two independent axes that must not be collapsed:

| Detector technology | afterSRC | in front of SAMURAI |
|---|---|---|
| External detectors | `afterSRC/` | `infrontofSamuraiMag/` |
| CompactOne in-vacuum detectors | required deployment profile | required deployment profile |

`afterSRC/` and `infrontofSamuraiMag/` are mature external-detector routes. They are not migration targets for CompactOne and must remain independently runnable.

## Current architecture assessment

### KEEP

- The stateful `target.yaml -> config -> generator -> validator -> artifacts -> state.json` pipeline and hash-based skip mechanism.
- The authoritative 12-channel placement model: D, P-small, and P-large in LEFT, RIGHT, UP, and DOWN sectors.
- Explicit elastic-coincidence pairing and machine-readable channel manifest.
- The common placement mathematics and target-centered coordinate convention.
- Existing square and cylindrical shell primitives.
- Existing separation of physical objects, purchased-component envelopes, interface envelopes, and keep-outs in the FreeCAD document.
- The baseline electrical concept: twelve independent 50-ohm coax paths, bias on signal coax through external bias tees, active electronics outside vacuum, temperature monitoring, spare capacity, grounding, and strain relief.
- The ICF70 rotary-interface envelope and WORK/PARK target-position semantics as a starting point.
- The external-route modules and their independent profiles, tests, worklogs, and artifacts.
- The report's staged-development concept: single detector, golden cassette, golden sector, then four-sector instrument.

### REFACTOR

- Split the monolithic `components.py` into detector, cassette, cartridge, target, chamber, services/feedthrough, thermal, and material-aware modules.
- Replace the conflated `detector.diameter_mm/length_mm` model with separate active plastic, optical package, SiPM, cassette, connector, and mounting envelopes.
- Replace twelve independent back-face support arms with four removable three-channel sector cartridges.
- Replace endpoint-only target checks with WORK, PARK, hard-stop, and complete swept-volume validation.
- Replace nominal center-ray/cylindrical LOS checks with full target-region-to-active-disc acceptance cones and component-level obstruction reports.
- Move electrical services out of `top_services` into a deployment-independent service architecture plus deployment-specific feedthrough placement.
- Add an explicit thermal conduction contract from SiPM to chamber/service structure.
- Treat beamline flanges as purchased-part contracts and welded stubs/transitions as project-designed components.
- Make chamber cross-section a candidate choice instead of a square-only validation contract.
- Generate separate cassette, sector, internal-machine, and deployment assemblies rather than only one whole-instrument document.
- Categorize validation results by physics, beamline, detector, cartridge, target, LOS, services, vacuum, mechanical, and thermal domains.
- Include source configuration dependencies in the state hash; the current hash only covers one YAML file and overrides.

### LEGACY / REFERENCE ONLY

- The 25 mm diameter by 50 mm long detector solid and annular clamp.
- The old central-spine concept and current twelve independent detector-back-face arms.
- The 440 mm square chamber as a geometry scaffold, not a CompactOne chamber requirement.
- The existing `example_jis_vf100.yaml` as a parser/geometry compatibility sample; it is not a CompactOne deployment definition.
- Project-drawn annular ICF/CF flange shapes as visual interface envelopes. They are not certified purchased parts.
- External-route target geometry as a source of motion and datum semantics only; it must not be copied dimension-for-dimension into CompactOne.
- The current service routing polylines as preliminary routing intent. Their displayed 25 mm bend-radius metadata is not yet enforced geometrically.

### MISSING

- A decision-status vocabulary consistently applied to all engineering values.
- A fast-plastic active element with independently configurable 5–6 mm prototype thickness.
- An optical coupling, reflector/light-treatment, and measured collection-efficiency contract.
- An EQR15 prototype-baseline SiPM definition with alternatives retained.
- A physically meaningful removable detector cassette with datums, anti-rotation, stop, thermal path, light-tight shell, strain relief, connector keep-out, and temperature sensor.
- A removable three-channel sector cartridge and a golden-sector artifact.
- A complete target subsystem including hard stop and full motion sweep.
- Component-level materials, density, vacuum-compatibility status, physics sensitivity, and path-material inventory.
- Full-acceptance LOS validation against target hardware, other cassettes, cartridges, services, and chamber structures.
- A feedthrough plate/manifold abstraction and bought-out component metadata.
- A strict structural sanity gate that rejects the current 63.6 mm OD / 63.0 mm ID, 0.30 mm radial-wall tube.
- Purchased-flange certified clear-bore checks.
- Thermal connectivity validation.
- Chamber screening metrics for square and cylindrical candidates: volume, approximate mass, access, cartridge clearance, and target sweep clearance.
- Separate CompactOne-afterSRC and CompactOne-infrontSamurai deployment profiles.
- Intentional failure regression tests.
- Reproducible subassembly FCStd/STEP/JSON artifacts.

## Confirmed contradictions and risks

| Finding | Current behavior | Required disposition |
|---|---|---|
| Strict mode is ignored | `validation.py` assigns `_ = strict`; strict and non-strict produce the same checks | Add severity and strict-only engineering gates |
| Non-fabricable beam stub passes | 63.6 mm OD and 63.0 mm ID gives 0.30 mm radial wall | Non-strict warning; strict failure |
| Active detector is conflated with housing | One 25 × 50 mm cylinder is reported as active geometry | Split active plastic from cassette and use active thickness for acceptance |
| Square chamber is falsely mandatory | Geometry supports cylindrical shells, validator requires square | Accept both and compare candidate metrics |
| Target sweep is absent | Only WORK geometry and PARK keep-out are built | Sample/fuse the complete motion sweep and validate it |
| LOS is incomplete | A constant-radius cylinder approximates active acceptance and aggregates all intersections | Build target-region-to-active-disc acceptance cones with per-component failures |
| Cable bend radius is metadata only | Routes are sharp segmented polylines | Model sweep envelopes or explicitly report unresolved routing |
| ICF precision is not evidence-backed | Project dimensions are drawn as if exact | Add purchased-part contract metadata and unresolved status |
| Report and CAD disagree | Report recommends fast plastic, 5–6 mm, EQR15, and 2–5%; CAD still uses a generic placeholder | Encode recommendations explicitly without promoting them to frozen values |
| SAMURAI CompactOne interface is unknown | External profile records VF100/VG80, but CompactOne has no site profile | Reuse only confirmed interface evidence; keep envelope and certified bore unresolved |

## Migration boundary

The first CompactOne implementation will preserve the existing module name and stateful entry point for compatibility. New common subsystem abstractions will replace the preferred assembly path. The old detector/support geometry will remain selectable as `legacy_scaffold` until migration tests and generated artifacts prove the new path.

