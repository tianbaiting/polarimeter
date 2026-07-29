import configparser
import math
import pathlib
import sys
import types

_fc = types.ModuleType("FreeCAD")


class _Vec:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def cross(self, other):
        return _Vec(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    @property
    def Length(self):
        return math.sqrt(self.dot(self))

    def normalize(self):
        length = self.Length
        if length <= 0.0:
            raise ValueError("cannot normalize zero vector")
        self.x /= length
        self.y /= length
        self.z /= length
        return self


_fc.Vector = _Vec
sys.modules["FreeCAD"] = _fc
sys.modules["Part"] = types.ModuleType("Part")
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from civ.config import load_config
from civ.components import rotary_target_center, top_service_port_specs
from civ.layout import (
    build_detector_placements,
    detector_center,
    norm,
    sector_direction_from_theta,
    target_facing_active_face_center,
)
from civ.manifest import build_channel_manifest


def _config_path(name: str) -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent / "config" / name


def _load_cfg(name: str = "default_compactInVacuum.yaml"):
    return load_config(str(_config_path(name)))


def test_sector_directions():
    for sector in ("left", "right", "up", "down"):
        direction = sector_direction_from_theta(20.9, sector)
        assert math.isclose(norm(direction), 1.0, rel_tol=0.0, abs_tol=1e-12)


def test_build_placements_count():
    placements = build_detector_placements(_load_cfg())
    assert len(placements) == 12


def test_placement_angles():
    cfg = _load_cfg()
    for placement in build_detector_placements(cfg):
        actual_angle = math.degrees(math.acos(max(-1.0, min(1.0, placement.direction.z / norm(placement.direction)))))
        assert math.isclose(actual_angle, placement.angle_deg, rel_tol=0.0, abs_tol=1e-9)


def test_placement_radii():
    for placement in build_detector_placements(_load_cfg()):
        assert math.isclose(norm(detector_center(placement)), placement.radius_mm, rel_tol=0.0, abs_tol=1e-6)


def test_target_facing_active_face_radii():
    cfg = _load_cfg()
    for placement in build_detector_placements(cfg):
        expected_radius_mm = placement.radius_mm - (0.5 * cfg.detector.length_mm)
        actual_radius_mm = norm(target_facing_active_face_center(placement, cfg.detector.length_mm))
        assert math.isclose(actual_radius_mm, expected_radius_mm, rel_tol=0.0, abs_tol=1e-6)


def test_unique_tags():
    placements = build_detector_placements(_load_cfg())
    tags = [placement.tag for placement in placements]
    assert len(tags) == len(set(tags))


def test_default_square_icf114_contract():
    cfg = _load_cfg()
    assert cfg.vessel.cross_section == "square"
    assert math.isclose(cfg.vessel.inner_size_x_mm, cfg.vessel.inner_size_y_mm, rel_tol=0.0, abs_tol=1e-9)
    assert cfg.vessel.contract.front_standard == "ICF114"
    assert cfg.vessel.contract.rear_standard == "ICF114"
    assert cfg.vessel.end_modules.front.standard == "ICF114"
    assert cfg.vessel.end_modules.rear.standard == "ICF114"
    assert cfg.vessel.beam_bore_diameter_mm <= cfg.vessel.end_modules.front.pipe_inner_diameter_mm


def test_physics_channel_manifest_contract():
    cfg = _load_cfg()
    manifest = build_channel_manifest(cfg, build_detector_placements(cfg))

    assert manifest["physics"]["reaction"] == "H1(d,d)p_elastic"
    assert manifest["physics"]["beam_kinetic_energy_mev"] == 380.0
    assert manifest["detector_model"]["active_medium_status"] == "undecided"
    assert manifest["detector_model"]["photosensor_status"] == "selected"
    assert manifest["schema_version"] == 3
    assert manifest["electrical_services"]["signal_impedance_ohm"] == 50.0
    assert len(manifest["electrical_services"]["signal_ports"]) == 4
    assert all(
        port["used_slots"] == [1, 2, 3] and port["spare_slots"] == [4]
        for port in manifest["electrical_services"]["signal_ports"]
    )

    channels = manifest["channels"]
    assert len(channels) == 12
    assert len({channel["channel_id"] for channel in channels}) == 12
    assert all("electrical_service" in channel for channel in channels)

    pairs = manifest["coincidence_pairs"]
    assert len(pairs) == 8
    opposite = {
        "left": "right",
        "right": "left",
        "up": "down",
        "down": "up",
    }
    for pair in pairs:
        assert pair["proton_sector"] == opposite[pair["deuteron_sector"]]

    forward_left = next(pair for pair in pairs if pair["pair_id"] == "forward_left")
    assert forward_left["deuteron_channel_id"] == "left_deuteron"
    assert forward_left["proton_channel_id"] == "right_proton_large"
    assert forward_left["branch"] == "forward"

    backward_up = next(pair for pair in pairs if pair["pair_id"] == "backward_up")
    assert backward_up["deuteron_channel_id"] == "up_deuteron"
    assert backward_up["proton_channel_id"] == "down_proton_small"
    assert backward_up["branch"] == "backward"

    pzz = manifest["observables"]["pzz"]
    pyy = manifest["observables"]["pyy"]
    assert len(pzz["numerator_pair_ids"]) == 4
    assert len(pzz["denominator_pair_ids"]) == 4
    assert len(pyy["lr_pair_ids"]) == 2
    assert len(pyy["ud_pair_ids"]) == 2


def test_top_service_interface_and_channel_capacity():
    cfg = _load_cfg()
    services = cfg.top_services
    assert services is not None
    assert services.icf70_interface.standard == "ICF70"
    assert services.rotary.mount_standard == "ICF70"
    assert len(top_service_port_specs(cfg)) == 5
    assert {port.sector for port in services.electrical.signal_ports} == {
        "left",
        "right",
        "up",
        "down",
    }
    capacity = (
        len(services.electrical.signal_ports)
        * services.electrical.channels_per_signal_port
    )
    assert capacity == 16
    assert capacity - services.electrical.detector_channel_count == 4


def test_rotary_target_work_and_park_centers():
    cfg = _load_cfg()
    rotary = cfg.top_services.rotary
    work = rotary_target_center(cfg, rotary.work_angle_deg)
    park = rotary_target_center(cfg, rotary.park_angle_deg)
    assert math.isclose(work.x, 0.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(work.y, 0.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(work.z, 0.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(park.x, 70.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(park.z, 70.0, rel_tol=0.0, abs_tol=1e-12)


def test_no_dedicated_monitoring_service_in_legacy_profile():
    cfg = _load_cfg()
    assert cfg.top_services is not None
    assert not hasattr(cfg.top_services.electrical, "housekeeping")
    assert {
        port.role
        for port in top_service_port_specs(cfg)
    } == {"rotary", "signal"}


def test_compact_analysis_config_matches_cad_source():
    cfg = _load_cfg()
    channel_by_name = {channel.name: channel for channel in cfg.channels}
    scenario_path = pathlib.Path(__file__).parents[2] / "code" / "config" / "compact_in_vacuum.ini"
    scenario = configparser.ConfigParser()
    scenario.read(scenario_path, encoding="utf-8")

    proton_angles = [float(value.strip()) for value in scenario["custom_layout"]["proton_theta_lab_deg"].split(",")]
    proton_distances = [float(value.strip()) for value in scenario["custom_layout"]["proton_distance_mm"].split(",")]
    proton_widths = [float(value.strip()) for value in scenario["custom_layout"]["proton_width_theta_mm"].split(",")]

    assert proton_angles == [
        channel_by_name["proton_large"].angle_deg,
        channel_by_name["proton_small"].angle_deg,
    ]
    assert proton_distances == [
        channel_by_name["proton_large"].radius_mm,
        channel_by_name["proton_small"].radius_mm,
    ]
    assert proton_widths == [cfg.detector.diameter_mm, cfg.detector.diameter_mm]
    assert float(scenario["custom_layout"]["deuteron_theta_lab_deg"]) == channel_by_name["deuteron"].angle_deg
    assert float(scenario["custom_layout"]["deuteron_distance_mm"]) == channel_by_name["deuteron"].radius_mm
    assert float(scenario["custom_layout"]["deuteron_width_theta_mm"]) == cfg.detector.diameter_mm
    assert float(scenario["beam"]["kinetic_energy_mev"]) == cfg.physics.beam.kinetic_energy_mev
    assert float(scenario["target"]["areal_density_g_per_m2"]) == cfg.physics.target.areal_density_g_per_m2
    assert float(scenario["run"]["coincidence_sector_multiplier"]) == 4.0
    assert scenario.getboolean("energy_loss", "enabled") is False


def test_jis_example_contract():
    cfg = _load_cfg("example_jis_vf100.yaml")
    assert cfg.vessel.cross_section == "square"
    assert cfg.vessel.contract.front_standard == "VF100"
    assert cfg.vessel.contract.rear_standard == "VF100"
    assert cfg.vessel.end_modules.front.standard == "VF100"
    assert cfg.vessel.end_modules.rear.standard == "VF100"
    assert math.isclose(cfg.vessel.beam_bore_diameter_mm, 80.0, rel_tol=0.0, abs_tol=1e-9)


def test_legacy_inner_diameter_maps_to_cylindrical(tmp_path):
    legacy_config = """
vessel:
  inner_diameter_mm: 440.0
  wall_thickness_mm: 10.0
  length_mm: 360.0
  center_z_mm: 130.0
  beam_bore_diameter_mm: 63.0
  end_modules:
    front:
      standard: ICF114
      module_outer_diameter_mm: 113.5
      module_inner_diameter_mm: 63.6
      pipe_outer_diameter_mm: 63.6
      pipe_inner_diameter_mm: 63.0
      pipe_length_mm: 80.0
      module_thickness_mm: 17.5
      seal_face_width_mm: 10.0
      bolt_circle_diameter_mm: 92.2
      bolt_count: 8
      flange_bolt_hole_diameter_mm: 8.4
      oring_groove_inner_diameter_mm: 0.0
      oring_groove_outer_diameter_mm: 0.0
      oring_groove_depth_mm: 0.0
      interface_bolt_diameter_mm: 8.0
      interface_bolt_length_mm: 35.0
      interface_nut_outer_diameter_mm: 13.0
      interface_nut_thickness_mm: 6.5
      interface_washer_outer_diameter_mm: 16.0
      interface_washer_thickness_mm: 1.5
    rear:
      standard: ICF114
      module_outer_diameter_mm: 113.5
      module_inner_diameter_mm: 63.6
      pipe_outer_diameter_mm: 63.6
      pipe_inner_diameter_mm: 63.0
      pipe_length_mm: 80.0
      module_thickness_mm: 17.5
      seal_face_width_mm: 10.0
      bolt_circle_diameter_mm: 92.2
      bolt_count: 8
      flange_bolt_hole_diameter_mm: 8.4
      oring_groove_inner_diameter_mm: 0.0
      oring_groove_outer_diameter_mm: 0.0
      oring_groove_depth_mm: 0.0
      interface_bolt_diameter_mm: 8.0
      interface_bolt_length_mm: 35.0
      interface_nut_outer_diameter_mm: 13.0
      interface_nut_thickness_mm: 6.5
      interface_washer_outer_diameter_mm: 16.0
      interface_washer_thickness_mm: 1.5
  contract:
    front_standard: ICF114
    rear_standard: ICF114
channels:
  - name: deuteron
    angle_deg: 20.9
    radius_mm: 140.0
    confidence: high
sectors: [left]
detector:
  diameter_mm: 25.0
  length_mm: 50.0
  clamp_outer_diameter_mm: 32.0
  clamp_width_mm: 12.0
inner_frame:
  spine_diameter_mm: 30.0
  arm_cross_width_mm: 20.0
  arm_cross_thickness_mm: 10.0
validation:
  angle_tolerance_deg: 0.05
  radius_tolerance_mm: 0.2
"""
    config_path = tmp_path / "legacy_compact.yaml"
    config_path.write_text(legacy_config, encoding="utf-8")
    cfg = load_config(str(config_path))
    assert cfg.vessel.cross_section == "cylindrical"
    assert math.isclose(cfg.vessel.inner_size_x_mm, 440.0, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(cfg.vessel.inner_size_y_mm, 440.0, rel_tol=0.0, abs_tol=1e-9)
