from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
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
    assert _check_by_name(report, "chamber", "end_module_fastener_hardware").passed
    assert _check_by_name(report, "chamber", "vacuum_boundary_complete").passed
    assert _check_by_name(report, "plates", "los_unobstructed_margin_5mm").passed
    los_scope = _check_by_name(report, "plates", "los_all_occluders_clear")
    assert los_scope.passed
    assert "scope=v1_conceptual" in los_scope.detail
    assert _check_by_name(report, "plates", "plate_to_stand_tie_hardware").passed
    assert _check_by_name(report, "detector", "clamp_fastening_and_key_features").passed
    assert _check_by_name(report, "detector", "no_detector_package_interference_with_assembly").passed
    assert _check_by_name(report, "target", "removable_holder_dual_screw_clamp").passed
    assert _check_by_name(report, "stand", "plate_tie_parameterized").passed


def test_h_plate_missing_up_sector_opening_is_caught() -> None:
    pytest.importorskip("FreeCAD")

    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements
    from ifsm.validation import ValidationThresholds, validate_constraints

    cfg = load_build_config(
        ROOT / "config" / "default_infront.yaml",
        overrides=["geometry.plate.h.azimuth_centers_deg=[0.0, 180.0, -90.0]"],
    )
    placements = build_detector_placements(cfg.layout)
    report = validate_constraints(placements, cfg.geometry, ValidationThresholds())

    los_occluder = _check_by_name(report, "plates", "los_all_occluders_clear")
    assert not los_occluder.passed
    assert "up_proton_large" in los_occluder.detail


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
