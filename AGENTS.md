# Repository Guidelines

## Stateful CAD Mandatory Rules

All Codex terminals working on CAD in this repository MUST use the module selected in
`codex_targets.yaml`; no root-level `afterSRC/` or `infrontofSamuraiMag/` module exists.

| Workstream | Role | Target | Runner | Requirement authority | Module worklog |
|---|---|---|---|---|---|
| `compactOneAfterSRC` | current baseline | `compactInVacuum/target_compact_one_afterSRC.yaml` | `compactInVacuum/run_compactOne_afterSRC.sh` | `docs/specs/compact_one_requirement_baseline.md` | `compactInVacuum/worklog.md` |
| `compactOneInfrontSamurai` | current baseline | `compactInVacuum/target_compact_one_infrontSamurai.yaml` | `compactInVacuum/run_compactOne_infrontSamurai.sh` | `docs/specs/compact_one_requirement_baseline.md` | `compactInVacuum/worklog.md` |
| `compactInVacuum` | compatibility scaffold | `compactInVacuum/target.yaml` | `compactInVacuum/run_compactInVacuum.sh` | `docs/specs/compact_one_requirement_baseline.md` | `compactInVacuum/worklog.md` |
| `afterSRC` | legacy external reference | `external_version/afterSRC/target.yaml` | `external_version/afterSRC/run_afterSRC.sh` | `docs/specs/BLP_v1_requirement_baseline.md` | `external_version/afterSRC/worklog.md` |
| `infrontofSamuraiMag` | legacy external reference | `external_version/infrontofSamuraiMag/target.yaml` | `external_version/infrontofSamuraiMag/run_infrontofSamuraiMag.sh` | `docs/specs/BLP_v1_requirement_baseline.md` | `external_version/infrontofSamuraiMag/worklog.md` |

For every selected workstream:

1. Follow `user intent -> target.yaml -> generator -> validator -> artifacts -> state.json`.
2. Treat targets/configuration/worklogs as human-owned and state/lock/validation outputs as machine-owned.
3. Never hand-edit `state.json`, `state.lock`, or generated validation reports.
4. Put requirement or parameter changes in the selected baseline and target/config before code edits.
5. Respect lock files. Wait or retry; never bypass the lock.
6. Use `--force-rebuild` only to intentionally bypass hash-skip optimization.
7. Append both the root and selected module worklogs after every stateful run, including validate-only runs.

## Progress and Status Reading

Read progress in this order:

1. `codex_targets.yaml` to resolve the selected module.
2. The selected requirement baseline.
3. The selected target and referenced configuration.
4. `worklog.md`.
5. The selected module worklog.
6. The selected state file.
7. The validation report referenced by the state file.

Interpret validation using all of `validation.status`, `validation.strict`, and the report summary.
A non-strict `pass` is an acceptable prototype geometry result, not a fabrication/release pass.
Only `strict=true` with `status=pass` may be described as passing a strict release gate. A
hash-skipped invocation may leave the previous successful state intact; verify the target hash and
stored validation result before calling it current.

## Standard CAD Commands

Current baselines:

- `./compactInVacuum/run_compactOne_afterSRC.sh --pipeline-index codex_targets.yaml`
- `./compactInVacuum/run_compactOne_infrontSamurai.sh --pipeline-index codex_targets.yaml`

Preserved legacy references:

- `./external_version/afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml`
- `./external_version/infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`

Add `--validate-only` for a validation-only run and `--strict-validation` only when intentionally
evaluating the strict evidence/release gate.

## Change and Delivery Policy

- Add tests under the selected module's tests directory when behavior changes.
- Do not commit generated CAD (`*.FCStd`, `*.step`), runtime state, locks, caches, or build trees.
- Every stateful-run worklog entry must include timestamp (UTC and local), command, key parameters,
  validation mode/result, and next action.
- Final handoff must list commands executed, validation result, and updated files.

## `code/` Reconstruction and Analysis Module
- Scope: `code/` contains ROOT-based reconstruction / plotting / analysis code for the polarimeter, separate from the stateful FreeCAD pipeline.
- Source files live under:
  - `code/src/`
  - `code/include/dpolar/`
  - `code/apps/`
  - `code/tests/`
  - `code/config/`
- Generated directories:
  - `code/build/`
  - `code/output/`
  These are generated artifacts and must not be committed.
- Environment:
  - ROOT-based work under `code/` MUST run inside the `micromamba` environment `anaroot-env`.
- Preferred configure/build flow:
  - `micromamba run -n anaroot-env cmake -S code -B code/build -DDPOLAR_BUILD_TESTS=ON`
  - `micromamba run -n anaroot-env cmake --build code/build`
- Preferred test flow:
  - `micromamba run -n anaroot-env ctest --test-dir code/build --output-on-failure`
- Main executable entrypoints:
  - `code/build/dpol_tool`
  - `code/build/dpol_batch`
- If analysis logic, CLI behavior, or numerical outputs change, update or add regression coverage in `code/tests/test_main.cpp` or additional tests under `code/tests/`.
- Keep scenario/config changes in `code/config/*.ini` instead of hard-coding constants into apps where practical.
- Treat ROOT plotting outputs as generated results; keep reproducible commands in commit messages or handoff notes instead of committing `code/output/`.

### Count-to-Polarization Skill
- Repository-local skill for count-based polarization inference:
  - `skills/dpolar-count-inference/SKILL.md`
- Use this skill when the request involves:
  - `pzz` / `pyy` inference from counts,
  - LR/UD asymmetry inversion,
  - profile likelihood or likelihood-curve plotting,
  - `infer-pzz`, `infer-pyy`, `infer-pzz-plot`, or `infer-pyy-plot`.
- Keep this skill separate from `skills/infront-freecad-engineering/SKILL.md`.
  Use `dpolar-count-inference` for statistical inference and likelihood plots under `code/`;
  use `infront-freecad-engineering` for FreeCAD/stateful geometry and mixed CAD-analysis workflows.

## FreeCAD Interactive Drawing and Review Rules
- For FreeCAD GUI or MCP-driven work, distinguish three tasks clearly:
  1) parametric model generation,
  2) geometry validation,
  3) drawing / screenshot generation for review.
- Resolve the selected workstream through `codex_targets.yaml`; ad-hoc GUI drawing must not bypass its target/config ownership rules.
- Before producing review drawings or screenshots, first confirm the geometry source:
  - current CompactInVacuum baseline output,
  - compatibility scaffold output, or
  - preserved external-reference output.
- Deprecated ad-hoc macro previews are not authoritative review geometry.
- Use beam-axis-consistent standard views when sharing geometry snapshots:
  - `Isometric`
  - `Front`
  - `Top`
  - `Right`
- When a user asks to “画图” / make FreeCAD visuals, default to screenshots or view captures unless they explicitly ask for a dimensioned engineering drawing.
- Do not present screenshots as manufacturing drawings; if dimensions or fabrication intent matter, validate against the selected module's requirement authority and resolved configuration first.
- For interactive review, prefer object-focused captures of the changed subsystem rather than whole-assembly clutter.

## Module Scope
- Current baseline stateful modules are `compactOneAfterSRC` and `compactOneInfrontSamurai`.
- `compactInVacuum` is a compatibility scaffold; the two modules under `external_version/` are preserved references.
- Any future module must adopt the same target/state contract and be registered in `codex_targets.yaml`.
