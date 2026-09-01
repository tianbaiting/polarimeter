---
name: infront-freecad-engineering
description: Build, validate, inspect, and capture review views for the polarimeter's stateful CompactInVacuum or preserved external-reference FreeCAD models, including coupled CAD-analysis checks. Use for geometry, exports, validation reports, detector placement, access/support studies, or FreeCAD screenshots. Use dpolar-count-inference instead for standalone count-to-polarization inference.
---

# Polarimeter FreeCAD Engineering

Use the stateful module registry; do not infer a module from an old directory name or screenshot.

## Select the workstream

Read `codex_targets.yaml`, then route as follows:

| Registry name | Role | Baseline | Runner | Module worklog |
|---|---|---|---|---|
| `compactOneAfterSRC` | current baseline | `docs/specs/compact_one_requirement_baseline.md` | `compactInVacuum/run_compactOne_afterSRC.sh` | `compactInVacuum/worklog.md` |
| `compactOneInfrontSamurai` | current baseline | `docs/specs/compact_one_requirement_baseline.md` | `compactInVacuum/run_compactOne_infrontSamurai.sh` | `compactInVacuum/worklog.md` |
| `compactInVacuum` | compatibility scaffold | `docs/specs/compact_one_requirement_baseline.md` | `compactInVacuum/run_compactInVacuum.sh` | `compactInVacuum/worklog.md` |
| `afterSRC` | legacy external reference | `docs/specs/BLP_v1_requirement_baseline.md` | `external_version/afterSRC/run_afterSRC.sh` | `external_version/afterSRC/worklog.md` |
| `infrontofSamuraiMag` | legacy external reference | `docs/specs/BLP_v1_requirement_baseline.md` | `external_version/infrontofSamuraiMag/run_infrontofSamuraiMag.sh` | `external_version/infrontofSamuraiMag/worklog.md` |

If the request does not identify a workstream, infer it only from current artifacts or ask when the
choice would change the design. `afterSRC` normally means the current compact baseline unless the
user explicitly asks for the external H+V+V reference.

## Stateful workflow

Before edits or runs, read:

1. `AGENTS.md`.
2. The selected baseline.
3. The selected target and referenced configuration.
4. `worklog.md` and the selected module worklog.
5. The selected state and referenced validation report, when present.

Put requirement changes in the baseline first and parameter changes in the target/config before
changing implementation code. Never hand-edit state, lock, or generated validation output.

Run the selected wrapper from the repository root:

```bash
./compactInVacuum/run_compactOne_afterSRC.sh --pipeline-index codex_targets.yaml
./compactInVacuum/run_compactOne_infrontSamurai.sh --pipeline-index codex_targets.yaml
./external_version/afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml
./external_version/infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml
```

Use `--validate-only` when artifacts are unnecessary, `--force-rebuild` only when intentionally
bypassing hash skip, and `--strict-validation` only when intentionally evaluating the strict
evidence/release gate. Use target/config or supported `--set` overrides for geometry parameters.

After every stateful invocation, append timestamp, command, parameters, validation mode/result, and
next action to both `worklog.md` and the selected module worklog.

## Interpret validation correctly

For CompactInVacuum reports inspect at least:

- `status`, `strict`, `validation_mode`, and `summary`;
- `categories`, `engineering_metrics`, and `resolved_configuration`;
- the state file's target hash and artifact paths.

For legacy external reports inspect the report status and subsystem/check summaries exposed by that
engine. A non-strict `pass` is a prototype geometry pass, not a fabrication/release pass. Claim a
strict release pass only when `strict=true`, `status=pass`, and all applicable evidence gates close.

For the current afterSRC access design, keep these distinctions explicit:

- ICF305 is the recommended all-metal maintenance opening.
- The removable closure carries no detector, support, datum, ground, or cable-restraint load.
- Permanent supports remain on permanent chamber walls.
- The sampled 12 mm release does not prove the complete reorientation and lift path.

## Tests

Use the selected module's own test entry. For the current CompactInVacuum engine:

```bash
./compactInVacuum/run_freecad_tests.sh
```

Do not reuse legacy test paths for CompactInVacuum or claim a geometry result from tests belonging
to another workstream.

## Interactive review views

Use FreeCAD MCP only when the GUI RPC server is available. Confirm the selected stateful artifact
before opening or capturing it. Prefer object-focused `Isometric`, `Front`, `Top`, and `Right`
captures. Screenshots are review evidence, not manufacturing drawings.

If RPC is unavailable, use the selected stateful wrapper for deterministic batch validation/export
and report that interactive captures were not produced. Do not fall back to removed ad-hoc macros.

## Coupled analysis

ROOT-based analysis must run in `anaroot-env`:

```bash
micromamba run -n anaroot-env cmake -S code -B code/build -DDPOLAR_BUILD_TESTS=ON
micromamba run -n anaroot-env cmake --build code/build
micromamba run -n anaroot-env ctest --test-dir code/build --output-on-failure
micromamba run -n anaroot-env ./code/build/dpol_tool <command> --scenario code/config/default.ini --output-dir <dir>
```

Use this branch only when geometry and analysis must be checked together. Route standalone `pzz`,
`pyy`, LR/UD, profile-likelihood, or likelihood-curve requests to
`skills/dpolar-count-inference/SKILL.md`.
