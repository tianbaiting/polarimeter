# CompactInVacuum Common Platform

Two compact in-vacuum polarimeters are the current baseline:

- `CompactInVacuum-afterSRC`, downstream of SRC;
- `CompactInVacuum-preSAMURAI`, before the SAMURAI terminal.

`compactInVacuum` is the compatibility directory and stateful entry point for their common detector platform. Existing runner/configuration labels `CompactOne-afterSRC` and `CompactOne-infrontSamurai` are retained temporarily to avoid breaking paths; they map to the two baseline instruments above.

The external afterSRC implementation in `afterSRC/` is retained as a legacy/fallback/reference route, not as a baseline instrument. The existing external SAMURAI-front work in `infrontofSamuraiMag/` is also preserved as reference engineering work. Neither external implementation is silently migrated into the compact platform.

## Architecture

The preferred subsystem hierarchy is:

`active detector -> detector cassette -> three-channel sector cartridge -> four-sector internal machine -> deployment chamber`

Shared concepts include the active plastic, optical package, SiPM, cassette, sector cartridge, cabling philosophy, electronics, calibration, thermal path, physics acceptance, and validation rules. Beamline interfaces, target integration, chamber envelope, ports, support, and external service space belong to deployment profiles and require independent site evidence.

The former 25 × 50 mm detector cylinder, annular clamp, and twelve independent arms are retained only as a legacy scaffold during migration.

The current preferred geometry now contains an independently validated golden cassette, one D/P-small/P-large golden sector, four sector cartridges, the rotary target work/park sweep, twelve signal paths, four temperature harnesses, grounding bonds, and square/cylindrical chamber candidates.

## Configuration

Configuration values carry explicit status:

- `FROZEN`
- `PROVISIONAL`
- `RECOMMENDED`
- `PLACEHOLDER`
- `PURCHASED-PART-CONTRACT`

The common detector platform and the two deployment profiles are kept separate. Missing site or supplier facts stay unresolved rather than receiving invented dimensions.

- Common detector/mechanics: `config/common_detector.yaml`
- CompactInVacuum-afterSRC deployment: `config/afterSRC_compact.yaml`
- CompactInVacuum-preSAMURAI deployment: `config/infrontSamurai_compact.yaml`
- old scaffold: `config/default_compactInVacuum.yaml`

See `MIGRATION.md` for old-to-new field and geometry mappings.

## Validation

Validation is organized by physics, beamline, detector, sector cartridge, target, LOS, services, vacuum, mechanical, and thermal categories.

Non-strict mode supports architecture and prototype iteration with visible warnings. Strict mode is an engineering gate and rejects physically impossible tube walls, incomplete cassettes/targets/services, blocked acceptance cones, invalid apertures, missing thermal paths, and invalid vacuum boundaries.

## Stateful generation

The legacy-scaffold compatibility entry remains:

```bash
./compactInVacuum/run_compactInVacuum.sh \
  --pipeline-index codex_targets.yaml \
  --validate-only
```

Use `--strict-validation` for the engineering gate and `--force-rebuild` only when intentionally bypassing the state hash.

Generated CAD and runtime state remain untracked. Validation reports and stable geometry metrics are the cross-machine comparison authority.

The two baseline CompactInVacuum deployment entries are:

```bash
./compactInVacuum/run_compactOne_afterSRC.sh \
  --pipeline-index codex_targets.yaml \
  --force-rebuild

./compactInVacuum/run_compactOne_infrontSamurai.sh \
  --pipeline-index codex_targets.yaml \
  --force-rebuild
```

Their default targets use non-strict prototype validation. A geometry or capacity failure still fails and suppresses export. `--strict-validation` additionally activates supplier, vacuum-material, access-closure, site-envelope, and pressure-vessel evidence gates; the current provisional platform is expected to fail those unresolved release gates.

## Prototype maturity

Recommended first-prototype candidates are a fast blue plastic scintillator, approximately 20 mm active diameter, 5–6 mm active thickness, an NDL EQR15 11-6060D-S SiPM, and a measured 2–5% total optical collection target. These are not frozen manufacturing requirements.

The CAD/runtime golden-cassette, golden-sector, target-sweep, LOS, service-route, and thermal-connectivity gates pass. Physical optical/thermal/vacuum tests, a resolved cartridge access closure, signed beamline and purchased-component drawings, and chamber external-pressure FEA are still required.

## Requirement authority

- CompactOne: `docs/specs/compact_one_requirement_baseline.md`
- External detector mechanics: `docs/specs/BLP_v1_requirement_baseline.md`
- Architecture migration audit: `docs/specs/compact_one_architecture_audit.md`
