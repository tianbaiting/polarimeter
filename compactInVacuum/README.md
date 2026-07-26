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

The compatibility entry point remains:

```bash
./compactInVacuum/run_compactInVacuum.sh \
  --pipeline-index codex_targets.yaml \
  --validate-only
```

Use `--strict-validation` for the engineering gate and `--force-rebuild` only when intentionally bypassing the state hash.

Generated CAD and runtime state remain untracked. Validation reports and stable geometry metrics are the cross-machine comparison authority.

## Prototype maturity

Recommended first-prototype candidates are a fast blue plastic scintillator, approximately 20 mm active diameter, 5–6 mm active thickness, an NDL EQR15 11-6060D-S SiPM, and a measured 2–5% total optical collection target. These are not frozen manufacturing requirements.

The current work still requires signed beamline and purchased-component drawings, golden-cassette and golden-sector tests, target-motion review, vacuum material qualification, thermal tests, and chamber external-pressure FEA.

## Requirement authority

- CompactOne: `docs/specs/compact_one_requirement_baseline.md`
- External detector mechanics: `docs/specs/BLP_v1_requirement_baseline.md`
- Architecture migration audit: `docs/specs/compact_one_architecture_audit.md`
