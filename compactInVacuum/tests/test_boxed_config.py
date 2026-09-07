from dataclasses import replace
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from civ.boxed.config import load_spec, load_deployment
from civ.config import load_config


def test_boxed_study_inherits_frozen_detector_geometry():
    path = ROOT / "studies/boxed_sector/config.yaml"
    cfg = load_config(str(path))
    s = load_spec(path)
    assert s.sector == "right"
    assert [(c.angle_deg, c.radius_mm) for c in cfg.channels] == [
        (20.9, 140.0),
        (11.2, 190.0),
        (53.4, 205.0),
    ]
    assert (
        cfg.compact_one.deployment.maintenance_access.selected.clear_bore_diameter_mm
        == 251.0
    )
    assert cfg.compact_one.deployment.support_frame is None


@pytest.mark.parametrize(
    "key,value,message",
    [
        ("sector", "up", "RIGHT"),
        ("radial_release_mm", 3.0, "disengage"),
        ("pin_bore_diameter_mm", 2.0, "clearance"),
        ("rotation_deg", 180, "90-degree"),
        ("carrier_r_max_mm", 210, "ordered"),
        ("cable_bend_radius_mm", 0.5, "bend radius"),
        ("grip_jaw_open_offset_mm", [14.0, 12.0, 0.0], "close from below"),
    ],
)
def test_invalid_study_geometry_is_rejected(tmp_path, key, value, message):
    data = yaml.safe_load((ROOT / "studies/boxed_sector/config.yaml").read_text())
    data["boxed_sector_study"][key] = value
    data.pop("extends", None)
    file = tmp_path / "config.yaml"
    file.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match=message):
        load_spec(file)


def test_unknown_parameter_does_not_silently_change_geometry(tmp_path):
    data = yaml.safe_load((ROOT / "studies/boxed_sector/config.yaml").read_text())
    data["boxed_sector_study"]["misspelled_dimension"] = 1
    data.pop("extends", None)
    file = tmp_path / "config.yaml"
    file.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="extra="):
        load_spec(file)


def test_study_overrides_are_applied_and_validated():
    path = ROOT / "studies/boxed_sector/config.yaml"
    assert load_spec(path, {"boxed_sector_study.lift_mm": 370.0}).lift_mm == 370
    with pytest.raises(ValueError, match="disengage"):
        load_spec(path, {"boxed_sector_study.radial_release_mm": 1.0})


@pytest.mark.parametrize(
    "profile", ["afterSRC_compact.yaml", "infrontSamurai_compact.yaml"]
)
def test_full_deployments_share_boxed_dimensions_and_keep_site_interfaces(profile):
    path = ROOT / "config" / profile
    cfg, s, d = load_config(str(path)), load_spec(path), load_deployment(path)
    assert d["removal_order"] == ["up", "right", "left", "down"]
    assert cfg.compact_one.deployment.boxed_support.mount_radius_mm == s.dock_plane_r_mm
    assert (
        cfg.compact_one.deployment.boxed_support.release_clearance_mm
        == s.radial_release_mm
    )
    assert all(
        cfg.compact_one.deployment.sector_mount(n).wall == "annular_support"
        for n in cfg.sectors
    )
    interfaces = (
        cfg.compact_one.deployment.front_interface.standard,
        cfg.compact_one.deployment.rear_interface.standard,
    )
    assert interfaces == (
        ("ICF114", "ICF114") if profile.startswith("after") else ("VF100", "VG80")
    )


@pytest.mark.parametrize(
    "key,value,message",
    [
        ("removal_order", ["down", "right", "left", "up"], "sequence"),
        ("turn_deg", {"up": 0, "right": 90, "left": 90, "down": 180}, "align"),
        ("journal_center_z_mm", 198, "behind"),
        ("downstream_translation_mm", -1, "positive"),
        ("lift_mm", float("nan"), "finite"),
        ("misspelled_dimension", 10.0, "extra="),
        ("retainer_depth_mm", 0.0, "positive"),
        ("upper_parked_loom_turn_z_mm", [220.0], "coordinates"),
    ],
)
def test_full_deployment_rejects_unsupported_handling_geometry(key, value, message):
    with pytest.raises(ValueError, match=message):
        load_deployment(
            ROOT / "config/afterSRC_compact.yaml", {f"boxed_deployment.{key}": value}
        )
