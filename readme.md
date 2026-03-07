# Deuteron Beam Polarimeter CAD Project

This repository contains CAD modeling assets, references, and automation scripts for deuteron beam polarimeter design.

## Design Intent

The project tracks two physical deployment contexts:

- `infrontofSamuraiMag`: polarimeter in front of the SAMURAI magnetic field region.
- `upstreamBLP`: upstream polarimeter closer to the beamline interface (high-intensity monitoring).

Current engineering automation focus is `infrontofSamuraiMag`.

## Reference Detector Geometry

Target detector front-face center constraints used by current layout scripts:

| Particle channel | Lab angle (deg) | Radius (mm) |
|---|---:|---:|
| deuteron | 20.9 | 560 |
| proton_small | 11.2 | 760 |
| proton_large | 53.4 | 820 |

Detector housing diameter: `phi 50 mm`.

## Repository Map

- `infrontofSamuraiMag/`: parameterized FreeCAD generation pipeline, validation, and exports.
- `upstreamBLP/`: placeholder for upstream model assets.
- `docs/`: beamline and RCNP/BLP reference material.
- `assets/readme/`: visual references and beamline schematic.
- `skills/infront-freecad-engineering/`: Codex skill for reproducible infront workflow.

## Modeling Modes

Use one of the two modes depending on the task:

1. Batch generation (`freecadcmd`)
- Best for reproducible artifact generation (`FCStd/STEP`) and CI-like validation.
- Main entry:
  - `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`

2. Interactive generation (MCP + FreeCAD GUI)
- Best for interactive model edits, screenshots, and iterative prompting.
- Requires FreeCAD GUI to stay open while MCP is used.

## FreeCAD MCP Quick Start

This environment uses Codex MCP registration name `freecad`.

1. Check MCP registration
```bash
codex mcp list
codex mcp get freecad
```

2. Ensure FreeCAD addon path is correct
- Active user data path on this machine:
  - `~/.local/share/FreeCAD/`
- Addon directory must contain:
  - `~/.local/share/FreeCAD/Mod/FreeCADMCP`

3. Start RPC server in FreeCAD GUI
- Open FreeCAD.
- Select workbench: `MCP Addon`.
- Click toolbar action: `Start RPC Server`.

4. Keep FreeCAD GUI running
- If GUI closes, MCP calls will fail until you reopen FreeCAD and start RPC again.

## Skill Entry Point

For repeatable engineering workflow, use:

- `skills/infront-freecad-engineering/SKILL.md`

The skill standardizes:
- strict validation first,
- artifact generation after validation,
- JSON report checks,
- failure handling when constraints are violated.

## Worklog Files

Mandatory handoff logs for Codex terminals/agents:
- `worklog.md` (cross-terminal index)
- `infrontofSamuraiMag/worklog.md` (module execution detail)

## Infront Workflow Entry

Detailed operational guide:

- `infrontofSamuraiMag/README.md`
