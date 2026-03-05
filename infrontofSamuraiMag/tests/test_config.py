from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ifsm.config import load_build_config

pytestmark = pytest.mark.pure_python


def test_load_default_config() -> None:
    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    assert cfg.geometry.beamline.axis == "z"
    assert cfg.geometry.chamber.end_modules.front_standard == "VG150"
    assert cfg.geometry.chamber.end_modules.rear_standard == "VF150"
    assert len(cfg.layout.channels) == 3
    assert set(cfg.layout.sectors) == {"left", "right", "up", "down"}
    assert {channel.confidence for channel in cfg.layout.channels} <= {"high", "medium", "low"}
    assert cfg.geometry.plate.h.stiffener_count >= 1
    assert cfg.geometry.plate.h.bolt_hole_count >= 2
    assert cfg.geometry.detector.clamp.support_mount_block_length_mm > 0.0
    assert cfg.geometry.plate.h.orientation == "horizontal"
    assert cfg.geometry.plate.h.mount_plane == "xz"
    assert cfg.geometry.plate.v1.orientation == "vertical"
    assert cfg.geometry.plate.v1.mount_plane == "xy"
    assert cfg.geometry.plate.v2.orientation == "vertical"
    assert cfg.geometry.plate.v2.mount_plane == "xy"
    assert cfg.geometry.chamber.end_modules.bolt_count >= 6
    assert cfg.geometry.chamber.end_modules.interface_bolt_diameter_mm > 0.0
    assert cfg.geometry.target.ladder.motor_mount_width_mm > 0.0
    assert cfg.geometry.detector.clamp.clamp_bolt_diameter_mm > 0.0
    assert cfg.geometry.detector.clamp.anti_rotation_key_depth_mm > 0.0
    assert cfg.geometry.target.holder.clamp_screw_diameter_mm > 0.0
    assert cfg.geometry.stand.plate_tie_column_diameter_mm > 0.0
    assert cfg.geometry.clearance.los_scope == "v1_conceptual"
    assert not cfg.geometry.chamber.los_channels.enabled


def test_override_core_size_and_output_basename() -> None:
    cfg = load_build_config(
        ROOT / "config" / "default_infront.yaml",
        overrides=[
            "geometry.chamber.core.size_z_mm=460.0",
            "output.basename=v1_override",
        ],
    )
    assert cfg.geometry.chamber.core.size_z_mm == pytest.approx(460.0)
    assert cfg.output.basename == "v1_override"


def test_invalid_sector_validation(tmp_path: Path) -> None:
    bad_config = (ROOT / "config" / "default_infront.yaml").read_text(encoding="utf-8")
    bad_config = bad_config.replace("[left, right, up, down]", "[left, diag, up, down]")
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(bad_config, encoding="utf-8")

    with pytest.raises(ValueError, match="layout.sectors"):
        load_build_config(config_path)


def test_plate_must_be_offset() -> None:
    with pytest.raises(ValueError, match="must be offset from beam axis"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.plate.h.offset_x_mm=0",
                "geometry.plate.h.offset_y_mm=0",
            ],
        )


def test_load_bearing_plate_requires_minimum_bolt_count() -> None:
    with pytest.raises(ValueError, match="bolt_hole_count"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.plate.h.bolt_hole_count=1",
            ],
        )


def test_invalid_vertical_plate_mount_plane() -> None:
    with pytest.raises(ValueError, match="vertical plate must use mount_plane=xy"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.plate.v1.mount_plane=xz",
            ],
        )


def test_invalid_h_plate_orientation() -> None:
    with pytest.raises(ValueError, match="plate.h must be horizontal"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.plate.h.orientation=vertical",
                "geometry.plate.h.mount_plane=xy",
            ],
        )


def test_invalid_end_module_bolt_count() -> None:
    with pytest.raises(ValueError, match="bolt_count"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.chamber.end_modules.bolt_count=4",
            ],
        )


def test_invalid_end_module_interface_bolt_diameter() -> None:
    with pytest.raises(ValueError, match="interface_bolt_diameter_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.chamber.end_modules.interface_bolt_diameter_mm=8.0",
            ],
        )


def test_invalid_target_hard_stop_span() -> None:
    with pytest.raises(ValueError, match="hard_stop_span_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.target.ladder.hard_stop_span_mm=200",
            ],
        )


def test_invalid_detector_clamp_bolt_pitch() -> None:
    with pytest.raises(ValueError, match="clamp_bolt_pitch_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.detector.clamp.clamp_bolt_pitch_mm=80",
            ],
        )


def test_invalid_holder_screw_diameter() -> None:
    with pytest.raises(ValueError, match="clamp_screw_diameter_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.target.holder.clamp_screw_diameter_mm=10",
            ],
        )


def test_invalid_stand_tie_bolt_diameter() -> None:
    with pytest.raises(ValueError, match="plate_tie_bolt_diameter_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.stand.plate_tie_bolt_diameter_mm=13",
            ],
        )


def test_invalid_los_scope() -> None:
    with pytest.raises(ValueError, match="los_scope"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.clearance.los_scope=v3_unknown",
            ],
        )


def test_v2_scope_requires_los_channels_enabled() -> None:
    with pytest.raises(ValueError, match="los_channels.enabled"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.clearance.los_scope=v2_fullpath",
            ],
        )
