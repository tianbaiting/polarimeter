# infrontofSamuraiMag User Guide

This module builds, validates, and exports the BLP v1 in-front polarimeter concept assembly.

## 1. Run Commands

Stateful pipeline entry (required for module work):

```bash
./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml
```

Force rebuild (bypass hash-skip):

```bash
./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --force-rebuild
```

Validate only (strict gate):

```bash
./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation
```

V2 full-path LOS trial (legacy mode with overrides):

```bash
./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation \
  --set geometry.clearance.los_scope=v2_fullpath \
  --set geometry.chamber.los_channels.enabled=true \
  --set geometry.chamber.los_channels.channel_diameter_mm=96.0 \
  --set geometry.chamber.los_channels.channel_start_z_mm=8.0 \
  --set geometry.chamber.los_channels.channel_length_mm=1600.0 \
  --report-json /tmp/infront_v2_los_report.json
```

## 2. CLI Options

- `--config <path>`: config file path.
- `--set <key=value>`: dotted override (repeatable).
- `--output-dir <path>`: override `output.dir`.
- `--basename <name>`: override `output.basename`.
- `--formats <csv>`: override output formats (`fcstd,step`).
- `--dump-resolved-config`: print normalized config snapshot.
- `--doc-name <name>`: FreeCAD document name.
- `--validate-only`: run validation without CAD export.
- `--strict-validation` / `--no-strict-validation`: exit non-zero on validation fail.
- `--report-json <path>`: explicit report path.
- `--angle-tol-deg <v>`: angle tolerance.
- `--radius-tol-mm <v>`: radius tolerance.
- `--pipeline-index <path>`: resolve target/state from root index.
- `--force-rebuild`: force run even if target hash unchanged.

## 3. Development Environment (Reproducible)

Create a dedicated virtual environment for tests and config checks:

```bash
python3 -m venv infrontofSamuraiMag/.venv-pytest
infrontofSamuraiMag/.venv-pytest/bin/pip install -r infrontofSamuraiMag/requirements-dev.txt
```

Run test gate:

```bash
infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q infrontofSamuraiMag/tests
```

Layered test gate with dependency precheck:

```bash
infrontofSamuraiMag/.venv-pytest/bin/python infrontofSamuraiMag/scripts/precheck_test_env.py --layer pure_python
infrontofSamuraiMag/.venv-pytest/bin/python infrontofSamuraiMag/scripts/precheck_test_env.py --layer freecad_runtime
PYTHON_BIN=infrontofSamuraiMag/.venv-pytest/bin/python ./infrontofSamuraiMag/run_tests_layered.sh pure_python
PYTHON_BIN=infrontofSamuraiMag/.venv-pytest/bin/python ./infrontofSamuraiMag/run_tests_layered.sh freecad_runtime
```

## 4. Config Structure (`config/default_infront.yaml`)

### 4.1 geometry.beamline
- `axis`
- `inlet_diameter_mm`

### 4.2 geometry.chamber
- `core.size_x_mm / size_y_mm / size_z_mm / wall_thickness_mm`
- `end_modules.front_standard / rear_standard`
- `end_modules.module_outer_diameter_mm / module_inner_diameter_mm / module_thickness_mm`
- `end_modules.seal_face_width_mm / bolt_circle_diameter_mm / bolt_count`
- `end_modules.oring_groove_width_mm / oring_groove_depth_mm`
- `end_modules.interface_bolt_* / interface_nut_* / interface_washer_*` (replaceable interface fastening hardware)
- `los_channels.enabled / channel_diameter_mm / channel_start_z_mm / channel_length_mm` (used by LOS v2 full-path channel cuts)

### 4.3 geometry.ports
- `main_pump / gauge_safety / rotary_feedthrough / spare`
- each port: `side / center_z_mm / inner_diameter_mm / outer_diameter_mm / length_mm`

### 4.4 geometry.plate.h / v1 / v2
- `orientation` (`horizontal` or `vertical`)
- `mount_plane` (`xz` for H, `xy` for V1/V2)
- pose: `z_mm / offset_x_mm / offset_y_mm`
- panel: `width_mm / height_mm / thickness_mm`
- LOS opening: `inner_radius_mm / outer_radius_mm / sector_opening_deg / azimuth_centers_deg[]`
- load-bearing: `lug_* / bolt_hole_* / stiffener_*`

### 4.5 geometry.detector
- `clamp`: detector body/clamp/support parameters
  - includes `support_mount_block_*` and `support_mount_hole_diameter_mm`
  - includes `clamp_ear_* / clamp_bolt_* / anti_rotation_key_*` for split-clamp fastening and anti-rotation key features
- `adapter_block`: fixed-angle transition block parameters

### 4.6 geometry.target
- `ladder`: 3-position ladder + drive semantics
  - includes `motor_mount_* / hard_stop_* / index_*`
- `holder`: removable holder and target thicknesses
  - includes `clamp_screw_*` for dual-screw clamp realization

### 4.7 geometry.stand
- base/support/anchor/leveling/shim parameters
- includes `plate_tie_*` for plate-to-stand load-transfer columns/caps/bolts

### 4.8 geometry.clearance
- `los_scope` (`v1_conceptual` or `v2_fullpath`)
- `los_margin_mm`
- `los_detector_active_face_offset_mm`
- `detector_front_to_chamber_mm`
- `detector_pair_min_gap_mm`
- service clearances

### 4.9 layout
- `sectors: [left, right, up, down]`
- `channels[]`: `name / angle_deg / radius_mm / confidence`

### 4.10 output
- `dir / basename / formats`

## 5. Validation Report

JSON report is grouped by subsystem:
- `chamber`
- `plates`
- `detector`
- `target`
- `stand`

Global pass condition requires all subsystem checks to pass.

## 6. Artifacts

Expected outputs:
- `*.FCStd`
- `*.step`
- `*.validation_report.json`
- `state.json` (stateful run record)
