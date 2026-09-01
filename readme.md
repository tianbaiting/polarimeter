# Deuteron Beam Polarimeter Engineering Repository

The current project baseline contains two compact in-vacuum polarimeters:

1. `CompactInVacuum-afterSRC`, downstream of SRC.
2. `CompactInVacuum-preSAMURAI`, before the SAMURAI terminal.

They share the detector head, three-channel sector-holder architecture, SiPM/scintillator
technology, passive in-vacuum services, calibration approach, and physics studies. Chamber
geometry, beam interfaces, target integration, supports, and maintenance envelopes remain
deployment-specific and must be verified independently.

The external-detector models are preserved under `external_version/` as legacy/reference routes.
Their H+V+V mechanics and historical interface assumptions are not requirements for either
current CompactInVacuum instrument.

## Current architecture

| Workstream | Status | Detector location | Mechanical authority |
|---|---|---|---|
| `compactOneAfterSRC` | current baseline prototype | in vacuum | `docs/specs/compact_one_requirement_baseline.md` |
| `compactOneInfrontSamurai` | current baseline prototype | in vacuum | `docs/specs/compact_one_requirement_baseline.md` |
| `compactInVacuum` | compatibility numerical/CAD scaffold | in vacuum | `docs/specs/compact_one_requirement_baseline.md` |
| `afterSRC` | legacy/reference | outside vacuum | `docs/specs/BLP_v1_requirement_baseline.md` |
| `infrontofSamuraiMag` | legacy/reference | outside vacuum | `docs/specs/BLP_v1_requirement_baseline.md` |

The current afterSRC screening profile uses a provisional 440 x 440 mm square chamber, a
420 mm body, and a top all-metal ICF305 maintenance opening. The removable blank flange owns no
detector support, locating datum, ground termination, or permanent cable restraint. ICF253 is the
rejected access comparison and ICF356 is the enlarged-envelope comparison. The first 12 mm holder
release is validated; the complete reorientation and lift through the port remains unresolved.
Beamline and service-interface values remain evidence-qualified and are not fabrication contracts.

## Repository map

- `compactInVacuum/`: current common platform, both baseline deployment profiles, compatibility
  scaffold, generator, validation, and tests.
- `external_version/afterSRC/`: preserved afterSRC external-detector reference.
- `external_version/infrontofSamuraiMag/`: preserved SAMURAI-front external-detector reference.
- `code/`: ROOT/C++ reconstruction, coincidence, polarization, and plotting tools.
- `docs/specs/compact_one_requirement_baseline.md`: current CompactInVacuum requirement authority.
- `docs/specs/BLP_v1_requirement_baseline.md`: legacy external-route requirement authority.
- `docs/polarimeter_detector/compact_in_vacuum_sipm_report/`: reproducible detector, vacuum,
  energy-loss, and procurement study.
- `docs/beamline_info/`: site-interface evidence and open questions.
- `codex_targets.yaml`: stateful module registry.
- `worklog.md`: cross-module execution and handoff history.

## CompactInVacuum platform

The common hierarchy is:

`active plastic -> optical package -> SiPM -> detector head -> three-channel sector holder -> four-sector internal assembly -> deployment chamber`

The recommended starting head uses a 20 mm diameter, 5.5 mm fast-blue plastic active element and
an NDL EQR15-class SiPM. These values remain prototype recommendations until supplier, optical,
vacuum, and bench-test gates close. Dedicated temperature and housekeeping hardware is not part of
schema 3.

Compatibility labels containing `CompactOne` remain in executable paths; the authoritative
instrument names are `CompactInVacuum-afterSRC` and `CompactInVacuum-preSAMURAI`.

See `compactInVacuum/README.md` for generation details.

## Stateful CAD workflow

The pipeline is:

`target.yaml -> resolved configuration -> generator -> validator -> FCStd/STEP/JSON -> state.json`

Current baseline entries:

```bash
./compactInVacuum/run_compactOne_afterSRC.sh --pipeline-index codex_targets.yaml
./compactInVacuum/run_compactOne_infrontSamurai.sh --pipeline-index codex_targets.yaml
```

Compatibility scaffold:

```bash
./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml
```

Preserved legacy references:

```bash
./external_version/afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml
./external_version/infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml
```

Targets and configuration are human-owned. Runtime state, locks, generated CAD, and validation
reports are machine-written. Interpret a result using both validation status and validation mode:
a non-strict pass is a prototype geometry pass, not a fabrication/release pass. Fabrication claims
require `strict=true`, `status=pass`, and closure of the applicable supplier, interface, access,
vacuum, site-envelope, and structural evidence gates.

## Cross-machine reproducibility

Compare Git commit, resolved configuration, FreeCAD/Python versions, validation mode/results,
solid counts and bounding boxes, volumes and screening masses, detector coordinates and physics
metrics, target states, service routing, and access checks. Byte-identical FCStd or STEP output is
not required.
