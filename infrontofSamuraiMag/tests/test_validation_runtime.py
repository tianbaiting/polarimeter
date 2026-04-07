from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def _check_by_name(report, subsystem_name: str, check_name: str):
    subsystem = next(item for item in report.subsystems if item.name == subsystem_name)
    return next(item for item in subsystem.checks if item.name == check_name)


def test_default_runtime_validation_passes_strict_gate() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements
    from ifsm.validation import ValidationThresholds, validate_constraints

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = build_detector_placements(cfg.layout)
    report = validate_constraints(placements, cfg.geometry, ValidationThresholds())

    assert report.status == "pass"
    end_module_standard = _check_by_name(report, "chamber", "end_module_standard")
    assert end_module_standard.passed
    assert "front=VF100" in end_module_standard.detail
    assert "rear=VG80" in end_module_standard.detail
    type_semantics = _check_by_name(report, "chamber", "end_module_type_semantics")
    assert type_semantics.passed
    assert "front=VF100[groove_depth=0.000]" in type_semantics.detail
    assert "rear=VG80[groove_depth=3.000]" in type_semantics.detail
    pipe_stub = _check_by_name(report, "chamber", "welded_pipe_stub_to_standard_flange")
    assert pipe_stub.passed
    assert "front[pipe_od=114.3,pipe_id=80.0,pipe_len=100.0]" in pipe_stub.detail
    assert "rear[pipe_od=89.1,pipe_id=80.0,pipe_len=20.0]" in pipe_stub.detail
    assert _check_by_name(report, "chamber", "end_module_fastener_hardware").passed
    assert _check_by_name(report, "chamber", "vacuum_boundary_complete").passed
    assert _check_by_name(report, "chamber", "channel_first_exit_face_by_sector").passed
    assert _check_by_name(report, "plates", "los_unobstructed_margin_5mm").passed
    opening = _check_by_name(report, "plates", "plate_opening_geometry_valid")
    assert opening.passed
    assert "style=los_tube" in opening.detail
    h_plate_relief = _check_by_name(report, "plates", "h_plate_relief_cones_clear")
    assert h_plate_relief.passed
    assert "overlap=0.000000" in h_plate_relief.detail
    plate_pose = _check_by_name(report, "plates", "plate_pose_valid_hvv")
    assert plate_pose.passed
    assert "h=horizontal/xz" in plate_pose.detail
    assert "v1=vertical/yz" in plate_pose.detail
    assert "v2=vertical/yz" in plate_pose.detail
    assert _check_by_name(report, "plates", "plate_min_envelope_margin_5mm").passed
    assert _check_by_name(report, "plates", "vv_clear_gap_vs_detector_outer_diameter").passed
    assert _check_by_name(report, "plates", "no_plate_chamber_overlap_after_cutout").passed
    assert _check_by_name(report, "plates", "all_plate_solids_outside_chamber").passed
    assert _check_by_name(report, "plates", "single_continuous_plate_solids").passed
    los_scope = _check_by_name(report, "plates", "los_all_occluders_clear")
    assert los_scope.passed
    assert "scope=v2_fullpath" in los_scope.detail
    assert "chamber_opening=cone_to_detector_front_face_circle" in los_scope.detail
    plate_tie_check = _check_by_name(report, "plates", "plate_to_stand_tie_hardware")
    assert plate_tie_check.passed
    assert "mode=disabled" in plate_tie_check.detail
    assert _check_by_name(report, "detector", "clamp_fastening_and_key_features").passed
    assert _check_by_name(report, "detector", "detector_mount_bridge_pose_fixed_relative_to_detector_body").passed
    assert _check_by_name(report, "detector", "detector_mount_hole_pattern_derived_from_fixture_direction").passed
    assert _check_by_name(report, "detector", "detector_mount_plate_landing_within_envelope").passed
    assert _check_by_name(report, "detector", "detector_mount_bolt_pattern_4hole_rectangular").passed
    assert _check_by_name(report, "detector", "detector_mount_base_and_plate_hole_alignment").passed
    assert _check_by_name(report, "detector", "detector_mount_fixture_structural_continuity").passed
    assert _check_by_name(report, "detector", "detector_mount_sector_plate_assignment").passed
    assert _check_by_name(report, "detector", "detector_mount_bridge_length_within_limit").passed
    assert _check_by_name(report, "detector", "no_detector_package_interference_with_assembly").passed
    assert _check_by_name(report, "target", "single_rotary_target_mode").passed
    assert _check_by_name(report, "target", "single_target_holder_dual_screw_clamp").passed
    assert _check_by_name(report, "target", "park_position_clears_beam_axis").passed
    stand_tie_check = _check_by_name(report, "stand", "plate_tie_parameterized")
    assert stand_tie_check.passed
    assert "mode=disabled" in stand_tie_check.detail
    stand_anchor = _check_by_name(report, "stand", "anchor_slots_and_leveling")
    assert stand_anchor.passed
    assert "base_plate=disabled" in stand_anchor.detail
    support_count = _check_by_name(report, "stand", "eight_point_support")
    assert support_count.passed
    assert "support_centers=8" in support_count.detail
    support_grids = _check_by_name(report, "stand", "support_grids_under_chamber_and_h_plate")
    assert support_grids.passed
    assert "chamber_rows_z=[-150.0, 950.0]" in support_grids.detail
    assert "x=[-60.0, 60.0]" in support_grids.detail
    assert "h_rows_z=[400.0, 840.0]" in support_grids.detail
    assert "x=[-224.0, 176.0]" in support_grids.detail
    vertical_clearance = _check_by_name(report, "stand", "support_feet_extend_below_vertical_plates")
    assert vertical_clearance.passed
    assert "vertical_plate_ymin=-822.000" in vertical_clearance.detail


def test_aftersrc_runtime_validation_passes_strict_gate() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements
    from ifsm.validation import ValidationThresholds, validate_constraints

    cfg = load_build_config(REPO_ROOT / "afterSRC" / "config" / "default_afterSRC.yaml")
    placements = build_detector_placements(cfg.layout)
    report = validate_constraints(placements, cfg.geometry, ValidationThresholds())

    assert report.status == "pass"
    end_module_standard = _check_by_name(report, "chamber", "end_module_standard")
    assert end_module_standard.passed
    assert "front=ICF114" in end_module_standard.detail
    assert "rear=ICF114" in end_module_standard.detail
    type_semantics = _check_by_name(report, "chamber", "end_module_type_semantics")
    assert type_semantics.passed
    assert "front=ICF114[groove_depth=0.000]" in type_semantics.detail
    assert "rear=ICF114[groove_depth=0.000]" in type_semantics.detail
    port_contract = _check_by_name(report, "chamber", "port_contract")
    assert port_contract.passed
    assert "enabled=('rotary_feedthrough',)" in port_contract.detail
    assert "forbidden=('main_pump', 'gauge_safety', 'spare')" in port_contract.detail
    rotary_mount = _check_by_name(report, "chamber", "rotary_mount_standard")
    assert rotary_mount.passed
    assert "expected=ICF70" in rotary_mount.detail
    assert "actual=ICF70" in rotary_mount.detail
    pipe_stub = _check_by_name(report, "chamber", "welded_pipe_stub_to_standard_flange")
    assert pipe_stub.passed
    assert "front[pipe_od=63.6,pipe_id=63.0,pipe_len=80.0]" in pipe_stub.detail
    assert "rear[pipe_od=63.6,pipe_id=63.0,pipe_len=80.0]" in pipe_stub.detail
    assert _check_by_name(report, "chamber", "vacuum_boundary_complete").passed
    vendor_reference = _check_by_name(report, "target", "vendor_rotary_feedthrough_reference")
    assert vendor_reference.passed
    assert "enabled=True" in vendor_reference.detail
    assert "model=ICF70MRMF50" in vendor_reference.detail
    assert "shape_count=3" in vendor_reference.detail


def test_default_runtime_stand_omits_monolithic_base_plate() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.components import build_stand
    from ifsm.config import load_build_config

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    stand_parts = build_stand(cfg.geometry)

    assert "StandBasePlate" not in stand_parts


def test_default_runtime_support_feet_follow_chamber_and_h_rows() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.components import build_stand
    from ifsm.config import load_build_config

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    stand_parts = build_stand(cfg.geometry)
    foot_centers = sorted(
        (
            shape.BoundBox.Center.x,
            shape.BoundBox.Center.z,
        )
        for name, shape in stand_parts.items()
        if name.startswith("StandSupportFoot_")
    )

    chamber_z_min = cfg.geometry.chamber.core.center_z_mm - 0.5 * cfg.geometry.chamber.core.size_z_mm
    chamber_z_max = cfg.geometry.chamber.core.center_z_mm + 0.5 * cfg.geometry.chamber.core.size_z_mm
    expected_chamber_zs = [
        chamber_z_min + cfg.geometry.stand.chamber_support_end_margin_mm,
        chamber_z_max - cfg.geometry.stand.chamber_support_end_margin_mm,
    ]
    expected_h_zs = [
        cfg.geometry.plate.h.z_mm - (0.5 * cfg.geometry.plate.h.height_mm - cfg.geometry.stand.h_plate_support_end_margin_mm),
        cfg.geometry.plate.h.z_mm + (0.5 * cfg.geometry.plate.h.height_mm - cfg.geometry.stand.h_plate_support_end_margin_mm),
    ]

    assert len(foot_centers) == 8
    chamber_supports = sorted(
        center for center in foot_centers if any(center[1] == pytest.approx(z) for z in expected_chamber_zs)
    )
    h_supports = sorted(
        center for center in foot_centers if any(center[1] == pytest.approx(z) for z in expected_h_zs)
    )

    assert len(chamber_supports) == 4
    assert len(h_supports) == 4
    assert sorted({item[0] for item in chamber_supports}) == pytest.approx(
        [
            -cfg.geometry.stand.chamber_support_pair_half_span_x_mm,
            cfg.geometry.stand.chamber_support_pair_half_span_x_mm,
        ]
    )
    assert sorted({item[1] for item in chamber_supports}) == pytest.approx(expected_chamber_zs)
    assert sorted({item[0] for item in h_supports}) == pytest.approx(
        [
            cfg.geometry.plate.h.offset_x_mm - cfg.geometry.stand.h_plate_support_pair_half_span_x_mm,
            cfg.geometry.plate.h.offset_x_mm + cfg.geometry.stand.h_plate_support_pair_half_span_x_mm,
        ]
    )
    assert sorted({item[1] for item in h_supports}) == pytest.approx(expected_h_zs)
    lowest_support_y = min(
        shape.BoundBox.YMin
        for name, shape in stand_parts.items()
        if name.startswith("StandSupportFoot_")
    )
    assert lowest_support_y == pytest.approx(-852.5)


def test_default_runtime_h_plate_reliefs_clear_crossing_detector_cones() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.components import build_all_plates, target_detector_front_face_cone
    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements, plate_key_for_sector

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = build_detector_placements(cfg.layout)
    h_plate = build_all_plates(cfg.geometry, placements=placements)["HPlate"]
    cone_front_face_radius_mm = 0.5 * cfg.geometry.detector.clamp.detector_diameter_mm

    overlaps = []
    for placement in placements:
        if plate_key_for_sector(placement.sector_name) == "h":
            continue
        cone = target_detector_front_face_cone(cfg.geometry, placement, cone_front_face_radius_mm)
        assert cone is not None
        common = h_plate.common(cone)
        overlaps.append(common.Volume if not common.isNull() else 0.0)

    assert overlaps
    assert overlaps == pytest.approx([0.0] * len(overlaps), abs=1e-3)


def test_fcstd_export_roundtrip_reloads_saved_shapes(tmp_path: Path) -> None:
    pytest.importorskip("FreeCAD")
    pytest.importorskip("FreeCADGui")

    import FreeCAD as App
    import FreeCADGui as Gui

    from ifsm.assembly import build_document
    from ifsm.config import load_build_config
    from ifsm.export import ensure_fcstd_gui_session, export_document

    ensure_fcstd_gui_session()
    assert App.GuiUp == 1
    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    output_cfg = replace(cfg.output, output_dir=tmp_path, basename="roundtrip_check", formats=("fcstd",))
    result = build_document(cfg, doc_name="roundtrip_check_doc")

    paths = export_document(result.document, result.export_objects, output_cfg)

    exported_path = paths["fcstd"]
    assert exported_path.exists()
    with ZipFile(exported_path) as archive:
        assert "GuiDocument.xml" in archive.namelist()
        assert "Document.xml" in archive.namelist()

    reopened = App.openDocument(str(exported_path))
    try:
        chamber = reopened.getObject("TargetChamberBody")
        rear_module = reopened.getObject("RearEndModule_VG80")
        assert chamber is not None
        assert rear_module is not None
        assert not chamber.Shape.isNull()
        assert not rear_module.Shape.isNull()
    finally:
        App.closeDocument(reopened.Name)
        if Gui.activeDocument() is not None:
            Gui.activeDocument().activeView().fitAll()


def test_legacy_annular_sector_plate_envelope_too_small_is_caught() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements
    from ifsm.validation import ValidationThresholds, validate_constraints

    cfg = load_build_config(
        ROOT / "config" / "profiles" / "legacy_center_preview_locked.yaml",
        overrides=["geometry.plate.h.width_mm=200.0"],
    )
    placements = build_detector_placements(cfg.layout)
    report = validate_constraints(placements, cfg.geometry, ValidationThresholds())

    envelope = _check_by_name(report, "plates", "plate_min_envelope_margin_5mm")
    assert not envelope.passed
    assert "h[w=" in envelope.detail


def test_signal_feedthrough_semantic_is_derived_from_port_fields() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.config import load_build_config
    from ifsm.validation import _validate_chamber

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    base_ports = cfg.geometry.ports

    @dataclass(frozen=True)
    class PortsWithSignal:
        main_pump: object
        gauge_safety: object
        rotary_feedthrough: object
        spare: object
        detector_signal: object

    fake_ports = PortsWithSignal(
        main_pump=base_ports.main_pump,
        gauge_safety=base_ports.gauge_safety,
        rotary_feedthrough=base_ports.rotary_feedthrough,
        spare=base_ports.spare,
        detector_signal=base_ports.spare,
    )
    geometry_with_signal = replace(cfg.geometry, ports=fake_ports)

    chamber_result = _validate_chamber(geometry_with_signal)
    no_signal = next(item for item in chamber_result.checks if item.name == "no_detector_signal_feedthrough_port")
    assert not no_signal.passed


def test_v2_los_scope_reports_fullpath_scope_string() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements
    from ifsm.validation import ValidationThresholds, validate_constraints

    cfg = load_build_config(
        ROOT / "config" / "default_infront.yaml",
        overrides=[
            "geometry.clearance.los_scope=v2_fullpath",
            "geometry.chamber.los_channels.enabled=true",
            "geometry.chamber.los_channels.channel_diameter_mm=96.0",
            "geometry.chamber.los_channels.channel_start_z_mm=8.0",
        ],
    )
    placements = build_detector_placements(cfg.layout)
    report = validate_constraints(placements, cfg.geometry, ValidationThresholds())

    los_scope = _check_by_name(report, "plates", "los_all_occluders_clear")
    assert "scope=v2_fullpath" in los_scope.detail
    assert "chamber_opening=cone_to_detector_front_face_circle" in los_scope.detail


def test_detector_bridge_pose_and_drill_axes_are_fixture_driven() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.components import detector_fixture_geometry
    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements, normalize, scaled

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = build_detector_placements(cfg.layout)

    reference_signature = None
    for placement in placements:
        layout = detector_fixture_geometry(cfg.geometry, placement)
        signature = (
            (layout.bridge_center - layout.front_center).dot(layout.direction),
            (layout.bridge_center - layout.front_center).dot(layout.mount_axis),
            (layout.bridge_center - layout.front_center).dot(layout.mount_lateral_axis),
        )
        if reference_signature is None:
            reference_signature = signature
        else:
            assert signature == pytest.approx(reference_signature)

        projected_direction = normalize(
            layout.direction - scaled(layout.plate_normal, layout.direction.dot(layout.plate_normal))
        )
        assert projected_direction.dot(layout.base_u_axis) == pytest.approx(1.0)
