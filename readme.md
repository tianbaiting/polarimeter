# Deuteron Beam Polarimeter Engineering Repository

Two compact in-vacuum polarimeters are the current project baseline:

1. **CompactInVacuum-afterSRC**, installed downstream of SRC.
2. **CompactInVacuum-preSAMURAI**, installed before the SAMURAI terminal.

Both instruments use the common CompactInVacuum detector platform: scintillator/SiPM technology, detector cassettes, vacuum detector services, electronics, calibration, and physics/response studies. Their chambers, beamline interfaces, target integration, supports, and maintenance envelopes are site-specific and shall be verified independently.

The previously developed afterSRC external-detector configuration is retained in `afterSRC/` as a legacy/fallback/reference route. It is not one of the two baseline instruments. Existing external-route code and evidence are preserved; they are not automatically requirements for either compact installation.

## Project architecture

| Item | afterSRC compact | pre-SAMURAI compact | legacy afterSRC external |
|---|---|---|---|
| Baseline status | baseline | baseline | legacy/fallback |
| Detector location | in vacuum | in vacuum | outside vacuum |
| Detector platform | common CompactInVacuum platform | common CompactInVacuum platform | established external design |
| Chamber geometry | site-specific / TBD | site-specific / TBD | existing reference geometry |
| Beam interfaces | verify from afterSRC site evidence | verify from pre-SAMURAI site evidence | existing legacy assumptions |

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

## Repository map

- `afterSRC/`: legacy/fallback external-detector afterSRC assembly using the established H+V+V family.
- `infrontofSamuraiMag/`: retained external-detector engineering work for the SAMURAI-front location; not a current baseline instrument.
- `compactInVacuum/`: compatibility module name for the common CompactInVacuum platform and its two baseline deployment profiles.
- `code/`: ROOT/C++ reconstruction, coincidence, polarization, and plotting tools.
- `docs/specs/BLP_v1_requirement_baseline.md`: external-route mechanical requirement authority.
- `docs/specs/compact_one_requirement_baseline.md`: CompactOne requirement authority.
- `docs/polarimeter_detector/compact_in_vacuum_sipm_report/`: reproducible SiPM, scintillator, energy-loss, vacuum, and procurement study.
- `docs/beamline_info/`: afterSRC and SAMURAI beamline-interface evidence and open questionnaires.
- `codex_targets.yaml`: stateful module registry.
- `worklog.md`: cross-module execution and handoff history.

## CompactInVacuum platform

The common platform separates:

`active plastic -> optical package -> SiPM -> removable cassette -> three-channel sector -> four-sector internal machine -> deployment chamber`

The platform shares detector and internal-machine concepts across afterSRC and pre-SAMURAI. Site-specific beamline interfaces, available envelopes, vacuum ports, external service space, support, and alignment live in deployment profiles. The compatibility labels `CompactOne-afterSRC` and `CompactOne-infrontSamurai` remain in scripts and configuration paths to avoid an unnecessary API/directory rename.

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
./compactInVacuum/run_compactOne_afterSRC.sh --pipeline-index codex_targets.yaml
./compactInVacuum/run_compactOne_infrontSamurai.sh --pipeline-index codex_targets.yaml
```

`target.yaml` and configuration files are human-owned. Runtime state, locks, generated CAD, and validation reports are machine-written.

`run_compactInVacuum.sh` preserves the legacy scaffold entry. The two `run_compactOne_*` commands generate the preferred shared internal machine with deployment-specific chambers.

Strict validation is the engineering acceptance gate. Non-strict CompactOne validation may retain explicit unresolved/prototype warnings, but it still rejects geometry, LOS, motion, service-capacity, aperture, and vacuum-boundary failures. Strict mode additionally rejects missing supplier, material, access, site-envelope, and structural-release evidence.

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
