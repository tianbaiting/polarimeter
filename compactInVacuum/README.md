# CompactOne / compactInVacuum

`compactInVacuum` is the compatibility name and stateful entry point for the CompactOne shared in-vacuum polarimeter platform.

CompactOne supports two deployment profiles:

- `CompactOne-afterSRC`
- `CompactOne-infrontSamurai`

It does not replace the external-detector implementations in `afterSRC/` or `infrontofSamuraiMag/`.

## Architecture

The preferred subsystem hierarchy is:

`active detector -> detector cassette -> three-channel sector cartridge -> four-sector internal machine -> deployment chamber`

Shared concepts include the active plastic, optical package, SiPM, cassette, sector cartridge, target mechanism, cabling philosophy, thermal path, physics acceptance, and validation rules. Beamline interfaces, chamber envelope, ports, support, and external service space belong to deployment profiles.

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
- afterSRC deployment: `config/afterSRC_compact.yaml`
- in-front-of-SAMURAI deployment: `config/infrontSamurai_compact.yaml`
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

The two preferred CompactOne deployment entries are:

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
