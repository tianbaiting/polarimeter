from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from civ.config import load_config
from civ.boxed.config import load_spec
from civ.boxed.side_config import load_side_spec


@pytest.mark.parametrize("profile", ["afterSRC", "infrontSamurai"])
def test_side_layout_preserves_detector_and_beam_contracts(profile):
    path = ROOT / f"config/{profile}_compact.yaml"
    cfg, s, q = load_config(str(path)), load_spec(path), load_side_spec(path)
    dep = cfg.compact_one.deployment
    assert dep.boxed_support is None and dep.local_support is not None
    assert dep.maintenance_access.wall == "positive_x_side"
    assert dep.maintenance_access.selected.clear_bore_diameter_mm == 251
    assert all(
        p.wall == ("positive_y_top" if p.role == "rotary" else "negative_x_side")
        for p in dep.service_ports
    )
    assert [(c.angle_deg, c.radius_mm) for c in cfg.channels] == [
        (20.9, 140),
        (11.2, 190),
        (53.4, 205),
    ]
    assert (dep.front_interface.standard, dep.rear_interface.standard) == (
        ("ICF114", "ICF114") if profile == "afterSRC" else ("VF100", "VG80")
    )
    assert s.radial_release_mm == dep.local_support.release_clearance_mm == 42
    assert q["removal_order"] == ["right", "down", "up", "left"]


@pytest.mark.parametrize(
    "key,value,message",
    [
        ("removal_order", ["up", "down", "left", "right"], "RIGHT"),
        ("capture_rod_y_offset_mm", 3, "journal"),
        ("wall_pad_thickness_mm", -1, "positive"),
        ("support_insertion_stage_z_mm", float("nan"), "finite"),
        ("unrecognized_distance", 12, "extra="),
    ],
)
def test_unsupported_side_parameters_fail(key, value, message):
    with pytest.raises(ValueError, match=message):
        load_side_spec(
            ROOT / "config/afterSRC_compact.yaml",
            {f"side_access_deployment.{key}": value},
        )


def test_rotary_cannot_silently_move_to_a_side_wall():
    cfg = ROOT / "config/afterSRC_compact.yaml"
    import yaml
    from civ.config import _load_yaml_file
    import tempfile

    raw = _load_yaml_file(cfg)
    raw["deployment"]["service_ports"][0]["wall"] = "negative_x_side"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "config.yaml"
        path.write_text(yaml.safe_dump(raw))
        with pytest.raises(ValueError, match="rotary"):
            load_config(str(path))
