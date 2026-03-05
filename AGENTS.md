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
- Active module runtime state: `infrontofSamuraiMag/state.json` (gitignored)
- Active module lock file: `infrontofSamuraiMag/state.lock` (gitignored)

Ownership rules:
- Human-owned: `codex_targets.yaml`, `target.yaml`
- Machine-owned: `state.json`, `state.lock`, validation report JSON

## Progress and Status Reading (Mandatory)
- Always read progress in this order:
  1) `codex_targets.yaml` (resolve active module/paths)
  2) `target.yaml` (intent + frozen spec/config refs)
  3) `state.json` (latest run status)
  4) validation report JSON path from `state.json.validation.report_json`
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
- Final report from a Codex terminal must include:
  - commands executed,
  - validation result,
  - updated files.

## Module Scope
- Current active stateful module: `infrontofSamuraiMag`.
- `upstreamBLP` is reserved for next phase. When activated, it must adopt the same target/state contract and be registered in `codex_targets.yaml`.
