# Deuteron Beam Polarimeter Engineering Repository

This repository develops deuteron-beam polarimeters for two physical installation locations and two independent detector-technology routes.

## Project matrix

| Detector technology | afterSRC | in front of SAMURAI |
|---|---|---|
| External detectors | `afterSRC/` | `infrontofSamuraiMag/` |
| CompactOne in-vacuum detectors | CompactOne afterSRC profile | CompactOne in-front-of-SAMURAI profile |

The existing external-detector routes are preserved. CompactOne is a parallel in-vacuum platform, not a rename or replacement of those modules.

## Repository map

- `afterSRC/`: stateful external-detector afterSRC assembly using the established H+V+V family.
- `infrontofSamuraiMag/`: stateful external-detector assembly for the SAMURAI-front location.
- `compactInVacuum/`: compatibility module name for the shared CompactOne in-vacuum platform and its two deployment profiles.
- `code/`: ROOT/C++ reconstruction, coincidence, polarization, and plotting tools.
- `docs/specs/BLP_v1_requirement_baseline.md`: external-route mechanical requirement authority.
- `docs/specs/compact_one_requirement_baseline.md`: CompactOne requirement authority.
- `docs/polarimeter_detector/compact_in_vacuum_sipm_report/`: reproducible SiPM, scintillator, energy-loss, vacuum, and procurement study.
- `docs/beamline_info/`: afterSRC and SAMURAI beamline-interface evidence and open questionnaires.
- `codex_targets.yaml`: stateful module registry.
- `worklog.md`: cross-module execution and handoff history.

## CompactOne

CompactOne separates:

`active plastic -> optical package -> SiPM -> removable cassette -> three-channel sector -> four-sector internal machine -> deployment chamber`

The platform shares detector and internal-machine concepts across afterSRC and SAMURAI. Site-specific beamline interfaces, available envelopes, vacuum ports, external service space, support, and alignment live in deployment profiles.

The first-prototype recommendations—fast blue plastic, approximately 20 mm active diameter, 5–6 mm thickness, EQR15 SiPM, and 2–5% measured total optical collection—remain recommendations until test gates close.

See `compactInVacuum/README.md`.

## Stateful CAD workflow

The common pipeline is:

`target.yaml -> resolved configuration -> generator -> validator -> FCStd/STEP/JSON -> state.json`

Main entries:

```bash
./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml
./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml
./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml
```

`target.yaml` and configuration files are human-owned. Runtime state, locks, generated CAD, and validation reports are machine-written.

Strict validation is the engineering acceptance gate. Non-strict CompactOne validation may retain explicit unresolved/prototype warnings; strict mode must reject placeholder engineering that would be unsafe or physically incoherent.

## Cross-machine reproducibility

The desk mini PC is the reference CAD environment. Laptop and labenpg reproduction shall compare:

- Git commit and resolved configuration;
- FreeCAD and Python versions;
- validation results;
- solid counts and bounding boxes;
- volumes and screening masses;
- detector centers, angles, acceptance values, and target states;
- service capacities and routing metrics.

Byte-identical FCStd or STEP files are not required.
