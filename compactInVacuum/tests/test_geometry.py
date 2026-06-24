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
from civ.layout import build_detector_placements, front_face_center, norm, sector_direction_from_theta


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
        assert math.isclose(norm(front_face_center(placement)), placement.radius_mm, rel_tol=0.0, abs_tol=1e-6)


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
