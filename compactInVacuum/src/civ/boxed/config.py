from __future__ import annotations

from dataclasses import dataclass, fields
import math
from pathlib import Path

import yaml


@dataclass(frozen=True)
class BoxSpec:
    sector: str
    cheek_inner_half_width_mm: float
    cheek_thickness_mm: float
    carrier_r_min_mm: float
    carrier_r_max_mm: float
    carrier_z_min_mm: float
    carrier_z_max_mm: float
    cheek_corner_radius_mm: float
    cheek_windows_mm: tuple[tuple[float, ...], ...]
    front_brace_mm: tuple[float, ...]
    rear_bridge_depth_mm: float
    rear_bridge_attachment_r_mm: float
    nest_boss_tangent_mm: float
    nest_boss_radius_mm: float
    clamp_width_local_x_mm: float
    side_attachment_local_x_mm: float
    side_bolt_radius_mm: float
    side_bolt_head_radius_mm: float
    side_bolt_head_depth_mm: float
    fastener_clearance_mm: float
    ring_inner_radius_mm: float
    ring_outer_radius_mm: float
    ring_front_z_mm: float
    ring_depth_mm: float
    wall_foot_width_mm: float
    dock_plane_r_mm: float
    dock_depth_mm: float
    dock_z_min_mm: float
    dock_z_max_mm: float
    pin_center_z_mm: float
    pin_tangent_spacing_mm: float
    pin_diameter_mm: float
    pin_projection_mm: float
    pin_bore_diameter_mm: float
    slot_length_mm: float
    draw_screw_head_mm: tuple[float, float, float]
    draw_screw_access_direction: tuple[float, float, float]
    draw_screw_shaft_radius_mm: float
    draw_screw_shaft_length_mm: float
    draw_screw_head_radius_mm: float
    draw_screw_head_depth_mm: float
    draw_screw_withdrawal_mm: float
    screwdriver_radius_mm: float
    screwdriver_length_mm: float
    grip_center_mm: tuple[float, float, float]
    grip_pin_radius_mm: float
    grip_pin_length_mm: float
    grip_head_radius_mm: float
    grip_bearing_clearance_mm: float
    grip_head_depth_mm: float
    grip_rod_radius_mm: float
    grip_rod_length_mm: float
    grip_jaw_open_offset_mm: tuple[float, float, float]
    grip_fork_half_width_mm: float
    grip_fork_plate_depth_mm: float
    grip_fork_anchor_r_mm: float
    grip_relief_z_half_span_mm: float
    cable_radius_mm: float
    cable_bend_radius_mm: float
    connector_radius_mm: float
    connector_body_length_mm: float
    connector_r_mm: float
    connector_z_mm: tuple[float, float, float]
    cable_turn_r_mm: tuple[float, float, float]
    cable_lane_y_mm: tuple[float, float, float]
    cable_lane_merge_r_mm: tuple[float, float, float]
    large_angle_cable_turn_z_mm: float
    connector_plug_length_mm: float
    connector_plug_collar_radius_mm: float
    connector_plug_collar_depth_mm: float
    connector_withdrawal_mm: float
    connector_parking_x_mm: float
    connector_parking_y_mm: float
    parking_clip_outer_radius_mm: float
    parking_clip_bore_radius_mm: float
    parking_clip_y_mm: tuple[float, ...]
    parking_backplate_mm: tuple[float, ...]
    ground_parking_pegs_mm: tuple[float, ...]
    ground_parking_peg_radius_mm: float
    ground_parking_backplate_mm: tuple[float, ...]
    ground_parking_translation_mm: tuple[float, ...]
    ground_bond_radius_mm: float
    radial_release_mm: float
    downstream_translation_mm: float
    rotation_deg: float
    lift_mm: float
    neighbor_r_min_mm: float
    neighbor_r_max_mm: float
    neighbor_half_width_mm: float
    neighbor_z_min_mm: float
    neighbor_z_max_mm: float
    continuous_clearance_mm: float
    interval_min_fraction: float
    interval_max_depth: int
    collision_volume_tolerance_mm3: float

    @property
    def half_width(self) -> float:
        return self.cheek_inner_half_width_mm + self.cheek_thickness_mm


def load_spec(path: str | Path, overrides=None) -> BoxSpec:
    raw = yaml.safe_load(Path(path).read_text())["boxed_sector_study"]
    raw.update(
        {
            key.split(".", 1)[1]: value
            for key, value in (overrides or {}).items()
            if key.startswith("boxed_sector_study.")
        }
    )
    names = {f.name for f in fields(BoxSpec)}
    if set(raw) != names:
        raise ValueError(
            f"boxed-sector keys differ: missing={names-set(raw)}, extra={set(raw)-names}"
        )
    vector_names = {
        "draw_screw_head_mm",
        "draw_screw_access_direction",
        "grip_center_mm",
        "grip_jaw_open_offset_mm",
        "connector_z_mm",
        "cable_turn_r_mm",
        "cable_lane_y_mm",
        "cable_lane_merge_r_mm",
        "front_brace_mm",
        "parking_clip_y_mm",
        "parking_backplate_mm",
        "ground_parking_pegs_mm",
        "ground_parking_backplate_mm",
        "ground_parking_translation_mm",
    }
    parsed = {}
    for name, value in raw.items():
        if name == "sector":
            if value != "right":
                raise ValueError("this detailed study implements the RIGHT sector only")
            parsed[name] = value
        elif name == "cheek_windows_mm":
            if (
                not isinstance(value, list)
                or not value
                or any(
                    len(row) != 5
                    or not all(math.isfinite(float(v)) and float(v) > 0 for v in row)
                    for row in value
                )
            ):
                raise ValueError(
                    "cheek windows require positive x,z,width,height,radius rows"
                )
            parsed[name] = tuple(tuple(map(float, row)) for row in value)
        elif name in vector_names:
            if (
                not isinstance(value, list)
                or len(value)
                != (
                    4
                    if name == "front_brace_mm"
                    else (
                        2
                        if name == "parking_clip_y_mm"
                        else (
                            5
                            if name
                            in {
                                "parking_backplate_mm",
                                "ground_parking_pegs_mm",
                                "ground_parking_backplate_mm",
                            }
                            else 3
                        )
                    )
                )
                or not all(math.isfinite(float(v)) for v in value)
            ):
                raise ValueError(f"{name} has invalid coordinates")
            parsed[name] = tuple(map(float, value))
        else:
            if (
                isinstance(value, bool)
                or not math.isfinite(float(value))
                or float(value) <= 0
            ):
                raise ValueError(f"{name} must be finite and positive")
            parsed[name] = int(value) if name == "interval_max_depth" else float(value)
    spec = BoxSpec(**parsed)
    if (
        not spec.carrier_r_min_mm
        < spec.carrier_r_max_mm
        < spec.ring_inner_radius_mm
        < spec.ring_outer_radius_mm
    ):
        raise ValueError("carrier and ring radii must be ordered")
    if spec.pin_bore_diameter_mm <= spec.pin_diameter_mm:
        raise ValueError("locating bores must provide positive pin clearance")
    if spec.radial_release_mm <= spec.pin_projection_mm:
        raise ValueError("release must disengage the full pin projection")
    if spec.cable_bend_radius_mm <= 2 * spec.cable_radius_mm:
        raise ValueError("cable bend radius is too small for the modeled section")
    if spec.rotation_deg != 90:
        raise ValueError(
            "the RIGHT-sector tool-channel certificate covers a 90-degree turn"
        )
    if (
        not spec.connector_radius_mm
        < spec.parking_clip_bore_radius_mm
        < spec.connector_plug_collar_radius_mm
        < spec.parking_clip_outer_radius_mm
    ):
        raise ValueError("parking bore must clear the plug shaft and retain its collar")
    return spec
