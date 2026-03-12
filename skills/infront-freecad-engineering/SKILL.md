---
name: infront-freecad-engineering
description: Build and validate the infrontofSamuraiMag FreeCAD model, capture review drawings/views, and run the polarimeter `code/` analysis workflow with reproducible CLI commands.
---

# infront FreeCAD Engineering Skill

Use this skill when the user asks to modify, generate, export, draw, screenshot, or validate the `infrontofSamuraiMag` model, or when the request couples geometry work with the `code/` reconstruction / plotting workflow.

## Trigger Conditions

Apply this skill when user requests include any of:
- `infrontofSamuraiMag`
- FreeCAD model generation or export
- FreeCAD screenshots, review views, or drawing-style snapshots
- detector angle/radius constraint checks
- validation report or strict geometry acceptance
- `code/` reconstruction, ROOT plotting, or ratio / LRUD / coincidence studies

## MCP Preflight Checklist

Before interactive MCP actions, verify all items below:

1. FreeCAD GUI is open.
2. `MCP Addon` workbench is selected in FreeCAD.
3. `Start RPC Server` has been clicked.
4. Codex MCP registration exists:
   - `codex mcp list`
   - `codex mcp get freecad`
5. Addon is installed in active FreeCAD user directory:
   - `~/.local/share/FreeCAD/Mod/FreeCADMCP` (current environment)
6. Decide whether the task is:
   - stateful CAD generation/validation,
   - interactive FreeCAD drawing/screenshot capture,
   - or `code/` analysis / plotting.

## Workflow

1. Read context files before any edit/run:
   - `docs/specs/BLP_v1_requirement_baseline.md`
   - `AGENTS.md`
   - `worklog.md`
   - `infrontofSamuraiMag/worklog.md`
2. If the task is geometry/config work, edit physical parameters in `infrontofSamuraiMag/config/default_infront.yaml` or pass one-off overrides with `--set`.
3. Run strict validation first for stateful geometry changes:
   - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
4. If validation passes, generate artifacts:
   - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`
5. Inspect report keys:
   - `status`, `thresholds`, `channels`, `subsystems`, `artifacts`
6. Fail fast rule:
   - If `status=fail`, do not claim geometry is acceptable; adjust config or tolerances.
7. Confirm runtime state:
   - `infrontofSamuraiMag/state.json` should have `validation.status=pass`.
8. After every stateful run (including `--validate-only`), append one entry to both:
   - `worklog.md`
   - `infrontofSamuraiMag/worklog.md`
   Entry fields (English): timestamp, command, key params/overrides, validation result, next action.

## `code/` Workflow

Use this branch of the skill when the user is asking for analysis code, plotting logic, or numerical study outputs rather than CAD geometry.

1. Read the build entrypoints:
   - `code/CMakeLists.txt`
   - `code/apps/dpol_tool.cpp`
   - `code/apps/dpol_batch.cpp`
   - `code/tests/test_main.cpp`
2. Configure out-of-tree:
   - `cmake -S code -B code/build -DDPOLAR_BUILD_TESTS=ON`
3. Build:
   - `cmake --build code/build`
4. Run regression test gate:
   - `ctest --test-dir code/build --output-on-failure`
5. Use `dpol_tool` for targeted studies:
   - `./code/build/dpol_tool validate-transform --scenario code/config/default.ini`
   - `./code/build/dpol_tool ratio --scenario code/config/default.ini --mode proton --output-dir code/output/manual_ratio`
   - `./code/build/dpol_tool coincidence --scenario code/config/default.ini --output-dir code/output/manual_coincidence`
6. Use `dpol_batch` for the full pre-defined workflow:
   - `./code/build/dpol_batch --scenario code/config/default.ini --output-dir code/output/manual_batch`
7. Treat `code/build/` and `code/output/` as generated only; do not commit them.
8. If analysis behavior changes, update test coverage under `code/tests/`.

## FreeCAD Drawing / Screenshot Workflow

Use this branch when the user asks to “画图”, get review images, or inspect a subsystem visually.

1. Decide the source model before drawing:
   - stateful `infrontofSamuraiMag` output for authoritative geometry
   - `infrontofSamuraiMag/build_polarimeter.py` only for quick reference previews
2. Build or validate the source geometry first; do not draw from a stale or unvalidated assembly if the request is meant to review current parameters.
3. Capture standard review views in this default order:
   - `Isometric`
   - `Front`
   - `Top`
   - `Right`
4. Focus on the changed object or subsystem when possible to reduce clutter.
5. Use screenshots / viewport captures for review unless the user explicitly requests dimensioned engineering drawings.
6. Do not describe screenshots as fabrication-ready drawings; dimension authority comes from validated parameters and requirement docs, not viewport images alone.
7. If MCP/GUI is unavailable, fall back to batch validation/export and state clearly that no interactive drawing capture was produced.

## Stable Commands

- Dump merged config:
  - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --dump-resolved-config`
- Tighten tolerance:
  - `--angle-tol-deg <deg> --radius-tol-mm <mm>`
- Disable hard failure temporarily:
  - `--no-strict-validation`
- Stateful run from root index:
  - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`
- `code/` configure:
  - `cmake -S code -B code/build -DDPOLAR_BUILD_TESTS=ON`
- `code/` build:
  - `cmake --build code/build`
- `code/` tests:
  - `ctest --test-dir code/build --output-on-failure`
- Single-study analysis:
  - `./code/build/dpol_tool <command> --scenario code/config/default.ini --output-dir <dir>`
- Batch analysis:
  - `./code/build/dpol_batch --scenario code/config/default.ini --output-dir <dir>`

## Fallback Rule (RPC Unavailable)

If MCP RPC is unavailable or FreeCAD GUI is not running:

1. Do not continue interactive MCP calls.
2. Fall back to deterministic batch validation:
   - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
3. Continue with batch export only after validation passes.
4. For `code/` tasks, continue with CLI build/test/plot commands because they do not depend on MCP.

## Notes

- Legacy-mode default strict thresholds are `0.05 deg` and `0.2 mm`.
- `--validate-only` skips FCStd/STEP generation and focuses on constraint acceptance.
- For reproducible history, keep `--basename` unique per iteration.
- Keep FreeCAD GUI open for MCP-driven operations.
- In this repository, “画图” may mean either FreeCAD geometry screenshots or ROOT physics plots; decide which branch is intended before acting.
