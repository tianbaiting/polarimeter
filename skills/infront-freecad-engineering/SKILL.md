---
name: infront-freecad-engineering
description: Build and validate the infrontofSamuraiMag FreeCAD model with strict geometry constraints, JSON validation reports, and reproducible CLI workflows.
---

# infront FreeCAD Engineering Skill

Use this skill when the user asks to modify, generate, export, or validate the `infrontofSamuraiMag` model.

## Trigger Conditions

Apply this skill when user requests include any of:
- `infrontofSamuraiMag`
- FreeCAD model generation or export
- detector angle/radius constraint checks
- validation report or strict geometry acceptance

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

## Workflow

1. Edit physical parameters in `infrontofSamuraiMag/config/default_infront.yaml` or pass one-off overrides with `--set`.
2. Run strict validation first:
   - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
3. If validation passes, generate artifacts:
   - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`
4. Inspect report keys:
   - `status`, `thresholds`, `channels`, `subsystems`, `artifacts`
5. Fail fast rule:
   - If `status=fail`, do not claim geometry is acceptable; adjust config or tolerances.
6. Confirm runtime state:
   - `infrontofSamuraiMag/state.json` should have `validation.status=pass`.

## Stable Commands

- Dump merged config:
  - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --dump-resolved-config`
- Tighten tolerance:
  - `--angle-tol-deg <deg> --radius-tol-mm <mm>`
- Disable hard failure temporarily:
  - `--no-strict-validation`
- Stateful run from root index:
  - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`

## Fallback Rule (RPC Unavailable)

If MCP RPC is unavailable or FreeCAD GUI is not running:

1. Do not continue interactive MCP calls.
2. Fall back to deterministic batch validation:
   - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
3. Continue with batch export only after validation passes.

## Notes

- Legacy-mode default strict thresholds are `0.05 deg` and `0.2 mm`.
- `--validate-only` skips FCStd/STEP generation and focuses on constraint acceptance.
- For reproducible history, keep `--basename` unique per iteration.
- Keep FreeCAD GUI open for MCP-driven operations.
