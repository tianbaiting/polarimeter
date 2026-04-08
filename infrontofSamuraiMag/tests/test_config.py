from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ifsm.config import load_build_config

pytestmark = pytest.mark.pure_python


def test_load_default_config() -> None:
    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    assert cfg.geometry.beamline.axis == "z"
    assert cfg.geometry.chamber.core.size_x_mm == pytest.approx(185.0)
    assert cfg.geometry.chamber.core.size_y_mm == pytest.approx(185.0)
    assert cfg.geometry.chamber.core.size_z_mm == pytest.approx(1200.0)
    assert cfg.geometry.chamber.core.center_z_mm == pytest.approx(400.0)
    assert cfg.geometry.chamber.end_modules.front_standard == "VF100"
    assert cfg.geometry.chamber.end_modules.rear_standard == "VG80"
    assert cfg.geometry.chamber.end_modules.front.pipe_length_mm == pytest.approx(100.0)
    assert cfg.geometry.chamber.end_modules.rear.pipe_length_mm == pytest.approx(20.0)
    assert cfg.geometry.chamber.contract.front_standard == "VF100"
    assert cfg.geometry.chamber.contract.rear_standard == "VG80"
    assert cfg.geometry.chamber.contract.required_ports_enabled == (
        "main_pump",
        "gauge_safety",
        "rotary_feedthrough",
        "spare",
    )
    assert cfg.geometry.ports.main_pump.center_z_mm == pytest.approx(-120.0)
    assert cfg.geometry.ports.gauge_safety.center_z_mm == pytest.approx(-140.0)
    assert cfg.geometry.ports.spare.center_z_mm == pytest.approx(-160.0)
    assert cfg.geometry.ports.main_pump.enabled is True
    assert cfg.geometry.ports.gauge_safety.enabled is True
    assert cfg.geometry.ports.rotary_feedthrough.enabled is True
    assert cfg.geometry.ports.spare.enabled is True
    assert len(cfg.layout.channels) == 3
    assert set(cfg.layout.sectors) == {"left", "right", "up", "down"}
    assert {channel.confidence for channel in cfg.layout.channels} <= {"high", "medium", "low"}
    assert cfg.geometry.plate.h.stiffener_count >= 1
    assert cfg.geometry.plate.h.bolt_hole_count >= 2
    assert cfg.geometry.detector.clamp.mount_base_u_mm > 0.0
    assert cfg.geometry.plate.h.orientation == "horizontal"
    assert cfg.geometry.plate.h.mount_plane == "xz"
    assert cfg.geometry.plate.h.offset_mode == "manual"
    assert cfg.geometry.plate.h.opening_style == "los_tube"
    assert cfg.geometry.plate.v1.orientation == "vertical"
    assert cfg.geometry.plate.v1.mount_plane == "yz"
    assert cfg.geometry.plate.v1.offset_mode == "manual"
    assert cfg.geometry.plate.v1.opening_style == "los_tube"
    assert cfg.geometry.plate.v2.orientation == "vertical"
    assert cfg.geometry.plate.v2.mount_plane == "yz"
    assert cfg.geometry.plate.v2.offset_mode == "manual"
    assert cfg.geometry.plate.v2.opening_style == "los_tube"
    assert cfg.geometry.chamber.end_modules.front.bolt_count >= 6
    assert cfg.geometry.chamber.end_modules.rear.bolt_count == 4
    assert cfg.geometry.chamber.end_modules.front.interface_bolt_diameter_mm > 0.0
    assert cfg.geometry.chamber.end_modules.rear.interface_bolt_diameter_mm > 0.0
    assert cfg.geometry.target.mode == "single_rotary"
    assert cfg.geometry.target.rotary is not None
    assert cfg.geometry.target.single_holder is not None
    assert cfg.geometry.target.rotary.motor_mount_width_mm > 0.0
    assert cfg.geometry.target.rotary.vendor_reference_enabled is False
    assert cfg.geometry.detector.clamp.clamp_bolt_diameter_mm > 0.0
    assert cfg.geometry.detector.clamp.anti_rotation_key_depth_mm > 0.0
    assert cfg.geometry.detector.adapter_block.radial_standoff_mm == pytest.approx(0.0)
    assert cfg.geometry.target.single_holder.clamp_screw_diameter_mm > 0.0
    assert cfg.geometry.stand.enable_plate_ties is False
    assert cfg.geometry.stand.with_base_plate is False
    assert cfg.geometry.stand.chamber_support_height_mm == pytest.approx(760.0)
    assert cfg.geometry.stand.chamber_support_end_margin_mm == pytest.approx(50.0)
    assert cfg.geometry.stand.chamber_support_pair_half_span_x_mm == pytest.approx(60.0)
    assert cfg.geometry.stand.h_plate_support_end_margin_mm == pytest.approx(100.0)
    assert cfg.geometry.stand.h_plate_support_pair_half_span_x_mm == pytest.approx(200.0)
    assert cfg.geometry.clearance.los_scope == "v2_fullpath"
    assert cfg.geometry.clearance.vv_min_gap_factor == pytest.approx(2.0)
    assert cfg.geometry.clearance.plate_auto_gap_mm == pytest.approx(5.0)
    assert cfg.geometry.clearance.plate_chamber_cutout_margin_mm == pytest.approx(5.0)
    assert cfg.geometry.chamber.los_channels.enabled
    assert cfg.geometry.ports.rotary_feedthrough.center_x_mm == pytest.approx(70.0)


def test_load_afterSRC_config_contract() -> None:
    cfg = load_build_config(REPO_ROOT / "afterSRC" / "config" / "default_afterSRC.yaml")

    assert cfg.geometry.beamline.inlet_diameter_mm == pytest.approx(63.0)
    assert cfg.geometry.chamber.end_modules.front_standard == "ICF114"
    assert cfg.geometry.chamber.end_modules.rear_standard == "ICF114"
    assert cfg.geometry.chamber.end_modules.front.pipe_length_mm == pytest.approx(80.0)
    assert cfg.geometry.chamber.end_modules.rear.pipe_length_mm == pytest.approx(80.0)
    assert cfg.geometry.chamber.contract.front_standard == "ICF114"
    assert cfg.geometry.chamber.contract.rear_standard == "ICF114"
    assert cfg.geometry.chamber.contract.required_ports_enabled == ("rotary_feedthrough",)
    assert cfg.geometry.chamber.contract.forbidden_ports_enabled == (
        "main_pump",
        "gauge_safety",
        "spare",
    )
    assert cfg.geometry.chamber.contract.rotary_mount_standard == "ICF70"
    assert cfg.geometry.ports.main_pump.enabled is False
    assert cfg.geometry.ports.gauge_safety.enabled is False
    assert cfg.geometry.ports.spare.enabled is False
    assert cfg.geometry.ports.rotary_feedthrough.enabled is True
    assert cfg.geometry.ports.rotary_feedthrough.length_mm == pytest.approx(8.0)
    assert cfg.geometry.ports.rotary_feedthrough.interface is not None
    assert cfg.geometry.ports.rotary_feedthrough.interface.standard == "ICF70"
    assert cfg.geometry.target.rotary is not None
    assert cfg.geometry.target.rotary.vendor_reference_enabled is True
    assert cfg.geometry.target.rotary.vendor_reference_model_code == "ICF70MRMF50"
    assert cfg.geometry.detector.adapter_block.radial_standoff_mm == pytest.approx(0.0)
    assert cfg.output.basename == "afterSRC"


def test_legacy_profile_still_parses_linear_ladder() -> None:
    cfg = load_build_config(ROOT / "config" / "profiles" / "legacy_center_preview_locked.yaml")
    assert cfg.geometry.target.mode == "linear_ladder"
    assert cfg.geometry.target.ladder is not None
    assert cfg.geometry.target.holder is not None
    assert cfg.geometry.target.ladder.active_index == 1


def test_override_core_size_and_output_basename() -> None:
    cfg = load_build_config(
        ROOT / "config" / "default_infront.yaml",
        overrides=[
            "geometry.chamber.core.size_z_mm=640.0",
            "geometry.chamber.core.center_z_mm=0.0",
            "output.basename=v1_override",
        ],
    )
    assert cfg.geometry.chamber.core.size_z_mm == pytest.approx(640.0)
    assert cfg.geometry.chamber.core.center_z_mm == pytest.approx(0.0)
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
                "geometry.plate.h.offset_mode=manual",
                "geometry.plate.h.offset_x_mm=0",
                "geometry.plate.h.offset_y_mm=0",
            ],
        )


def test_invalid_plate_offset_mode() -> None:
    with pytest.raises(ValueError, match="offset_mode"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.plate.v1.offset_mode=semi_auto",
            ],
        )


def test_auto_plate_offset_resolution_applies_minimum_gap() -> None:
    cfg = load_build_config(
        ROOT / "config" / "default_infront.yaml",
        overrides=[
            "geometry.plate.h.offset_mode=auto",
            "geometry.plate.h.offset_y_mm=0",
            "geometry.clearance.plate_auto_gap_mm=6.5",
        ],
    )
    expected = 0.5 * cfg.geometry.chamber.core.size_y_mm + 0.5 * cfg.geometry.plate.h.thickness_mm + 6.5
    assert cfg.geometry.plate.h.offset_y_mm == pytest.approx(expected)


def test_load_bearing_plate_requires_minimum_bolt_count() -> None:
    with pytest.raises(ValueError, match="bolt_hole_count"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.plate.h.bolt_hole_count=1",
            ],
        )


def test_invalid_vertical_plate_mount_plane() -> None:
    with pytest.raises(ValueError, match="plate.v1 must be vertical on yz plane"):
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
                "geometry.plate.h.mount_plane=xz",
            ],
        )


def test_invalid_end_module_bolt_count() -> None:
    with pytest.raises(ValueError, match="bolt_count"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.chamber.end_modules.rear.bolt_count=3",
            ],
        )


def test_invalid_end_module_interface_bolt_diameter() -> None:
    with pytest.raises(ValueError, match="interface_bolt_diameter_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.chamber.end_modules.rear.interface_bolt_diameter_mm=12.0",
            ],
        )


def test_end_module_pipe_stub_cannot_constrict_beamline() -> None:
    with pytest.raises(ValueError, match="pipe_inner_diameter_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.chamber.end_modules.front.pipe_inner_diameter_mm=60.0",
            ],
        )


def test_afterSRC_forbidden_side_port_must_stay_disabled() -> None:
    with pytest.raises(ValueError, match="forbidden_ports_enabled"):
        load_build_config(
            REPO_ROOT / "afterSRC" / "config" / "default_afterSRC.yaml",
            overrides=[
                "geometry.ports.main_pump.enabled=true",
            ],
        )


def test_afterSRC_rotary_mount_standard_must_match_interface() -> None:
    with pytest.raises(ValueError, match="rotary_mount_standard"):
        load_build_config(
            REPO_ROOT / "afterSRC" / "config" / "default_afterSRC.yaml",
            overrides=[
                "geometry.ports.rotary_feedthrough.interface.standard=ICF34",
            ],
        )


def test_core_center_z_must_keep_target_origin_inside_chamber() -> None:
    with pytest.raises(ValueError, match="center_z_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.chamber.core.center_z_mm=700.0",
            ],
        )


def test_invalid_target_hard_stop_span() -> None:
    with pytest.raises(ValueError, match="hard_stop_span_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.target.rotary.hard_stop_span_mm=200",
            ],
        )


def test_stand_support_half_span_must_fit_supported_footprints() -> None:
    with pytest.raises(ValueError, match="chamber_support_end_margin_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.stand.chamber_support_end_margin_mm=10.0",
            ],
        )

    with pytest.raises(ValueError, match="chamber_support_pair_half_span_x_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.stand.chamber_support_pair_half_span_x_mm=80.0",
            ],
        )

    with pytest.raises(ValueError, match="h_plate_support_pair_half_span_x_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.stand.h_plate_support_pair_half_span_x_mm=800.0",
            ],
        )

    with pytest.raises(ValueError, match="h_plate_support_end_margin_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.stand.h_plate_support_end_margin_mm=10.0",
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


def test_detector_adapter_radial_standoff_must_stay_zero() -> None:
    with pytest.raises(ValueError, match="radial_standoff_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.detector.adapter_block.radial_standoff_mm=5.0",
            ],
        )


def test_invalid_holder_screw_diameter() -> None:
    with pytest.raises(ValueError, match="clamp_screw_diameter_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.target.single_holder.clamp_screw_diameter_mm=10",
            ],
        )


def test_rotary_arm_length_must_match_pivot() -> None:
    with pytest.raises(ValueError, match="arm_length_mm must equal pivot_x_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.target.rotary.arm_length_mm=80",
            ],
        )


def test_invalid_stand_tie_bolt_diameter() -> None:
    with pytest.raises(ValueError, match="plate_tie_bolt_diameter_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.stand.enable_plate_ties=true",
                "geometry.stand.plate_tie_bolt_diameter_mm=13",
            ],
        )


def test_disabled_plate_ties_allow_zero_tie_dimensions() -> None:
    cfg = load_build_config(
        ROOT / "config" / "default_infront.yaml",
        overrides=[
            "geometry.stand.enable_plate_ties=false",
            "geometry.stand.plate_tie_column_diameter_mm=0",
            "geometry.stand.plate_tie_cap_width_mm=0",
            "geometry.stand.plate_tie_cap_height_mm=0",
            "geometry.stand.plate_tie_cap_thickness_mm=0",
            "geometry.stand.plate_tie_bolt_diameter_mm=0",
        ],
    )
    assert cfg.geometry.stand.enable_plate_ties is False


def test_disabled_base_plate_allows_zero_anchor_slots() -> None:
    cfg = load_build_config(
        ROOT / "config" / "default_infront.yaml",
        overrides=[
            "geometry.stand.with_base_plate=false",
            "geometry.stand.anchor_slot_length_mm=0",
            "geometry.stand.anchor_slot_width_mm=0",
        ],
    )
    assert cfg.geometry.stand.with_base_plate is False


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
                "geometry.chamber.los_channels.enabled=false",
            ],
        )


def test_invalid_vv_min_gap_factor() -> None:
    with pytest.raises(ValueError, match="vv_min_gap_factor"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.clearance.vv_min_gap_factor=0.8",
            ],
        )


def test_invalid_plate_chamber_cutout_margin() -> None:
    with pytest.raises(ValueError, match="plate_chamber_cutout_margin_mm"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.clearance.plate_chamber_cutout_margin_mm=0",
            ],
        )


def test_vv_gap_must_satisfy_detector_outer_diameter_rule() -> None:
    with pytest.raises(ValueError, match="v1/v2 clear gap"):
        load_build_config(
            ROOT / "config" / "default_infront.yaml",
            overrides=[
                "geometry.clearance.vv_min_gap_factor=12.0",
            ],
        )
