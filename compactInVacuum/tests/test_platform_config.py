from __future__ import annotations

import pathlib
import sys

import pytest


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from civ.config import config_dependency_paths, load_config
from civ.stateflow import compute_config_hash
from civ.validation_rules import evaluate_config_rules, rule_status


CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"
ACCESS_STUDY_CONFIG_DIR = (
    pathlib.Path(__file__).parent.parent / "studies" / "access_port" / "config"
)


def test_two_compact_deployment_profiles_load() -> None:
    aftersrc = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    samurai = load_config(str(CONFIG_DIR / "infrontSamurai_compact.yaml"))

    assert aftersrc.compact_one is not None
    assert samurai.compact_one is not None
    assert aftersrc.compact_one.deployment.instrument_name == "CompactInVacuum-afterSRC"
    assert samurai.compact_one.deployment.instrument_name == "CompactInVacuum-preSAMURAI"
    assert aftersrc.compact_one.deployment.external_route_module == "afterSRC"
    assert samurai.compact_one.deployment.external_route_module == "infrontofSamuraiMag"
    assert aftersrc.compact_one.deployment.maintenance_access is not None
    assert samurai.compact_one.deployment.maintenance_access is None
    assert samurai.compact_one.deployment.sector_mount("up").wall == "positive_y"
    assert samurai.compact_one.deployment.sector_mount("up").wall_standoff_mm == 16.0
    assert len(aftersrc.channels) * len(aftersrc.sectors) == 12
    assert len(samurai.channels) * len(samurai.sectors) == 12


def test_active_detector_has_calculated_compact_head_depth() -> None:
    cfg = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    platform = cfg.compact_one
    assert platform is not None

    assert platform.detector.active.diameter_mm == 20.0
    assert platform.detector.active.thickness_mm == 5.5
    assert platform.detector.active.thickness_status == "recommended"
    assert platform.detector.sipm.model == "NDL EQR15 11-6060D-S"
    assert platform.detector.sipm.status == "recommended"
    assert platform.detector.head.carrier_envelope_mm == (14.0, 14.0, 1.2)
    assert platform.detector.physical_depth_mm == pytest.approx(9.7)
    assert (
        platform.detector.physical_depth_mm
        <= platform.detector.head.maximum_physical_depth_mm
        <= 18.0
    )
    assert platform.detector.head.cable_exit_length_mm == 3.0
    assert platform.detector.head.connector_keepout_length_mm == 20.0


@pytest.mark.parametrize(
    "removed_field",
    (
        "temperature_sensor",
        "temperature_sensor_status",
        "services.temperature_channels",
        "services.wires_per_temperature_channel",
        "services.temperature_harnesses",
        "services.housekeeping_pin_capacity",
        "deployment.housekeeping_interface",
    ),
)
def test_schema_v3_rejects_removed_monitoring_fields(removed_field: str) -> None:
    with pytest.raises(ValueError, match="rejects removed fields"):
        load_config(
            str(CONFIG_DIR / "afterSRC_compact.yaml"),
            overrides={removed_field: 1},
        )


@pytest.mark.parametrize(
    "removed_field",
    (
        "detector.cassette",
        "sector_cartridge",
        "detector.head.anti_rotation_tab_mm",
    ),
)
def test_schema_v3_rejects_superseded_mechanical_fields(
    removed_field: str,
) -> None:
    with pytest.raises(ValueError, match="rejects removed fields"):
        load_config(
            str(CONFIG_DIR / "afterSRC_compact.yaml"),
            overrides={removed_field: 1},
        )


def test_default_services_have_no_monitoring_or_housekeeping_role() -> None:
    cfg = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    platform = cfg.compact_one
    assert platform is not None
    assert {port.role for port in platform.deployment.service_ports} == {
        "rotary",
        "signal",
    }
    serialized = repr(platform).lower()
    assert "temperature" not in serialized
    assert "housekeeping" not in serialized


def test_repository_angles_remain_unchanged_pending_evidence() -> None:
    cfg = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    channels = {channel.name: channel for channel in cfg.channels}
    assert channels["proton_large"].angle_deg == pytest.approx(53.4)
    assert channels["proton_small"].angle_deg == pytest.approx(11.2)


def test_aftersrc_uses_only_square_while_samurai_retains_screening_choices() -> None:
    aftersrc = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml")).compact_one
    samurai = load_config(str(CONFIG_DIR / "infrontSamurai_compact.yaml")).compact_one
    assert aftersrc is not None
    assert samurai is not None

    assert aftersrc.deployment.selected_chamber_candidate == (
        "aftersrc_square_icf305_access"
    )
    assert {
        item.cross_section for item in aftersrc.deployment.chamber_candidates
    } == {"square"}
    assert {item.cross_section for item in samurai.deployment.chamber_candidates} == {
        "square",
        "cylindrical",
    }
    assert aftersrc.deployment.chamber.cross_section == "square"
    assert samurai.deployment.chamber.cross_section == "square"


def test_aftersrc_all_metal_maintenance_access_contract() -> None:
    platform = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml")).compact_one
    assert platform is not None
    access = platform.deployment.maintenance_access
    assert access is not None and access.enabled
    assert access.selected_candidate == "ICF305"
    assert access.selected.chamber_candidate == "aftersrc_square_icf305_access"
    assert access.selected.clear_bore_diameter_mm == pytest.approx(251.0)
    assert access.seal_type == "conflat_knife_edge_metal_gasket"
    assert access.seal_material == "oxygen_free_copper"
    assert not access.elastomer_seal_allowed
    assert access.helium_leak_rate_max_pa_m3_s == pytest.approx(1.0e-10)
    assert {candidate.standard for candidate in access.candidates} == {
        "ICF253",
        "ICF305",
        "ICF356",
    }
    mounts = {
        sector: platform.deployment.sector_mount(sector)
        for sector in ("left", "right", "up", "down")
    }
    assert mounts["up"].wall == "negative_x"
    assert mounts["up"].tangent_coordinate_mm == pytest.approx(180.0)
    assert mounts["up"].wall_standoff_mm == pytest.approx(75.0)
    assert mounts["up"].release_clearance_mm == pytest.approx(12.0)
    assert all(mount.wall != "positive_y" for mount in mounts.values())


@pytest.mark.parametrize(
    ("profile", "standard", "chamber", "length_mm", "clear_bore_mm"),
    (
        (
            "afterSRC_access_icf253.yaml",
            "ICF253",
            "aftersrc_square_icf253_access",
            360.0,
            198.5,
        ),
        (
            "afterSRC_access_icf305.yaml",
            "ICF305",
            "aftersrc_square_icf305_access",
            420.0,
            251.0,
        ),
        (
            "afterSRC_access_icf356.yaml",
            "ICF356",
            "aftersrc_square_icf356_access",
            480.0,
            301.8,
        ),
    ),
)
def test_aftersrc_access_study_profiles_select_matching_chambers(
    profile: str,
    standard: str,
    chamber: str,
    length_mm: float,
    clear_bore_mm: float,
) -> None:
    platform = load_config(str(ACCESS_STUDY_CONFIG_DIR / profile)).compact_one
    assert platform is not None
    access = platform.deployment.maintenance_access
    assert access is not None
    assert access.selected.standard == standard
    assert platform.deployment.chamber.name == chamber
    assert platform.deployment.chamber.length_mm == pytest.approx(length_mm)
    assert access.selected.clear_bore_diameter_mm == pytest.approx(clear_bore_mm)


def test_aftersrc_maintenance_access_rejects_elastomer_contract() -> None:
    cfg = load_config(
        str(CONFIG_DIR / "afterSRC_compact.yaml"),
        overrides={"deployment.maintenance_access.elastomer_seal_allowed": True},
    )
    rule = _rule_by_name(cfg, "maintenance_access_all_metal_contract")
    assert not rule.passed
    assert rule_status(rule, strict=False) == "fail"


def test_inherited_config_dependencies_are_hashed(tmp_path: pathlib.Path) -> None:
    base = tmp_path / "base.yaml"
    child = tmp_path / "child.yaml"
    base.write_text("value: 1\n", encoding="utf-8")
    child.write_text("extends: base.yaml\nchild: true\n", encoding="utf-8")

    assert config_dependency_paths(child) == (base.resolve(), child.resolve())
    first_hash = compute_config_hash(str(child), {})
    base.write_text("value: 2\n", encoding="utf-8")
    second_hash = compute_config_hash(str(child), {})
    assert first_hash != second_hash


def test_unknown_decision_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be one of"):
        load_config(
            str(CONFIG_DIR / "afterSRC_compact.yaml"),
            overrides={"detector.active.material_status": "selected"},
        )


def test_purchased_interface_and_project_transition_are_separate() -> None:
    cfg = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    deployment = cfg.compact_one.deployment
    interface = deployment.front_interface

    assert interface.status == "purchased-part-contract"
    assert interface.certified_drawing_reference == "unresolved"
    assert interface.transition_status == "provisional"
    assert interface.transition_outer_diameter_mm > interface.transition_inner_diameter_mm
    assert (interface.transition_outer_diameter_mm - interface.transition_inner_diameter_mm) / 2.0 > 0.30


def _rule_by_name(cfg, name: str):
    return next(rule for rule in evaluate_config_rules(cfg) if rule.name == name)


def test_point_three_mm_structural_tube_wall_is_strict_failure() -> None:
    cfg = load_config(
        str(CONFIG_DIR / "afterSRC_compact.yaml"),
        overrides={
            "deployment.front_interface.transition_outer_diameter_mm": 63.6,
            "deployment.front_interface.transition_inner_diameter_mm": 63.0,
        },
    )
    rule = _rule_by_name(cfg, "front_transition_minimum_sanity_wall")

    assert not rule.passed
    assert rule_status(rule, strict=False) == "warning"
    assert rule_status(rule, strict=True) == "fail"


def test_insufficient_signal_feedthrough_capacity_is_rejected() -> None:
    cfg = load_config(
        str(CONFIG_DIR / "afterSRC_compact.yaml"),
        overrides={"services.signal_feedthrough_count": 2},
    )
    rule = _rule_by_name(cfg, "fast_signal_channel_capacity")

    assert not rule.passed
    assert rule_status(rule, strict=False) == "fail"
    assert rule_status(rule, strict=True) == "fail"


def test_invalid_beam_aperture_is_rejected() -> None:
    cfg = load_config(
        str(CONFIG_DIR / "afterSRC_compact.yaml"),
        overrides={"deployment.front_interface.nominal_clear_bore_mm": 15.0},
    )
    rule = _rule_by_name(cfg, "certified_interface_aperture_compatible")

    assert not rule.passed
    assert rule_status(rule, strict=False) == "fail"
    assert rule_status(rule, strict=True) == "fail"


def test_strict_mode_changes_placeholder_outcomes() -> None:
    cfg = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    rule = _rule_by_name(cfg, "front_purchased_interface_contract_resolved")

    assert not rule.passed
    assert rule_status(rule, strict=False) == "warning"
    assert rule_status(rule, strict=True) == "fail"
