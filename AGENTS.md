# Repository Guidelines

## Codex Terminal Mandatory Rules
All Codex terminals working in this repository MUST follow this protocol.

1. Always use stateful entry when working on `infrontofSamuraiMag`:
   - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`
2. Follow this fixed pipeline:
   - User intent -> `target.yaml` (Spec) -> Generator -> Validator -> Artifacts -> `state.json`
3. `target.yaml` is human-edited. `state.json` is machine-written only.
4. Never hand-edit `state.json` or `state.lock`.
5. If target/spec changes, update `target.yaml` first, then rerun pipeline.
6. Default acceptance gate is strict validation (`status=pass`).
7. Use `--force-rebuild` only when you intentionally bypass skip optimization.
8. Respect lock files. If locked, wait or retry; do not bypass lock behavior.

## Mechanical Requirement Baseline
- Canonical requirement document for current mechanical design work:
  - `docs/specs/BLP_v1_requirement_baseline.md`
- Any Codex terminal working on chamber/clamp/plate/target/stand mechanics MUST read this file first.
- If implementation or discussion diverges from this baseline, update the baseline first, then implement.

## Stateful Files (Source of Truth)
- Root index: `codex_targets.yaml`
- Active module target: `infrontofSamuraiMag/target.yaml`
- Cross-terminal worklog index: `worklog.md`
- Module execution worklog: `infrontofSamuraiMag/worklog.md`
- Active module runtime state: `infrontofSamuraiMag/state.json` (gitignored)
- Active module lock file: `infrontofSamuraiMag/state.lock` (gitignored)

Ownership rules:
- Human-owned: `codex_targets.yaml`, `target.yaml`, `worklog.md`, `infrontofSamuraiMag/worklog.md`
- Machine-owned: `state.json`, `state.lock`, validation report JSON

## Progress and Status Reading (Mandatory)
- Always read progress in this order:
  1) `codex_targets.yaml` (resolve active module/paths)
  2) `target.yaml` (intent + frozen spec/config refs)
  3) `worklog.md` (cross-terminal context and handoff summary)
  4) `infrontofSamuraiMag/worklog.md` (module-level command/result timeline)
  5) `state.json` (latest run status)
  6) validation report JSON path from `state.json.validation.report_json`
- `state.json.run.status` semantics:
  - `pass`: current run executed and passed strict gate
  - `fail`: current run executed but validation failed
  - `error`: pipeline aborted with runtime/config error
  - `skipped`: hash-skip path reused previous valid artifacts
- Treat `skipped + validation.status=pass` as "currently acceptable and up-to-date for unchanged target hash", not as failure.

## Standard Commands
- Standard run:
  - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`
- Force rebuild:
  - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --force-rebuild`
- Validate-only gate:
  - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`

## Change and Delivery Policy
- Any requirement/parameter change MUST be represented in `target.yaml` and/or config before code edits.
- Any code behavior change SHOULD include tests under `infrontofSamuraiMag/tests/`.
- Do not commit generated CAD artifacts (`*.FCStd`, `*.step`) or runtime state files.
- After every stateful pipeline run (including `--validate-only`), append one entry to:
  - `worklog.md`
  - `infrontofSamuraiMag/worklog.md`
- Each worklog entry must include: timestamp (UTC+local), command, key overrides/parameters, validation result, and next action.
- Final report from a Codex terminal must include:
  - commands executed,
  - validation result,
  - updated files.

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

## FreeCAD Interactive Drawing and Review Rules
- For FreeCAD GUI or MCP-driven work, distinguish three tasks clearly:
  1) parametric model generation,
  2) geometry validation,
  3) drawing / screenshot generation for review.
- The authoritative build path for `infrontofSamuraiMag` remains the stateful pipeline; ad-hoc GUI drawing must not bypass target/config ownership rules.
- Before producing review drawings or screenshots, first confirm the geometry source:
  - stateful pipeline output (`infrontofSamuraiMag`)
  - or quick macro/reference preview (`infrontofSamuraiMag/build_polarimeter.py`)
- Use beam-axis-consistent standard views when sharing geometry snapshots:
  - `Isometric`
  - `Front`
  - `Top`
  - `Right`
- When a user asks to “画图” / make FreeCAD visuals, default to screenshots or view captures unless they explicitly ask for a dimensioned engineering drawing.
- Do not present screenshots as manufacturing drawings; if dimensions or fabrication intent matter, validate against `docs/specs/BLP_v1_requirement_baseline.md` and the parametric config first.
- For interactive review, prefer object-focused captures of the changed subsystem rather than whole-assembly clutter.

## Module Scope
- Current active stateful module: `infrontofSamuraiMag`.
- `upstreamBLP` is reserved for next phase. When activated, it must adopt the same target/state contract and be registered in `codex_targets.yaml`.
