from __future__ import annotations

import math
from pathlib import Path
from ..config import _load_yaml_file


def load_side_spec(path, overrides=None):
    raw = _load_yaml_file(Path(path).resolve())["side_access_deployment"]
    for key, value in (overrides or {}).items():
        if key.startswith("side_access_deployment."):
            raw[key.split(".", 1)[1]] = value
    names = set(
        """status removal_order turn_deg wall_pad_thickness_mm wall_pad_half_width_mm
        wall_pad_z_mm window_pad_z_mm wall_weld_leg_mm support_flange_thickness_mm
        support_flange_half_width_mm mount_screw_t_mm mount_screw_z_offsets_mm
        mount_screw_center_z_mm window_screw_center_z_mm mount_screw_radius_mm
        mount_screw_head_radius_mm mount_screw_head_depth_mm mount_screw_blind_end_offset_mm
        mount_driver_radius_mm mount_driver_length_mm window_rib_thickness_mm
        support_insertion_offset_x_mm support_insertion_inboard_mm support_insertion_stage_z_mm
        support_insertion_stage_y_mm capture_rod_y_offset_mm capture_approach_raise_mm
        capture_insertion_offset_x_mm retainer_tangential_clearance_mm side_extraction_mm
        retainer_side_extraction_mm loom_front_z_mm loom_approach_x_mm loom_approach_step_mm
        loom_entry_turn_abs_y_mm""".split()
    )
    if set(raw) != names:
        raise ValueError(
            f"side-access keys differ: missing={names-set(raw)}, extra={set(raw)-names}"
        )
    if raw["removal_order"] != ["right", "down", "up", "left"]:
        raise ValueError("side extraction requires RIGHT, DOWN, UP, LEFT")
    if raw["turn_deg"] != {"right": 0, "down": 90, "up": -90, "left": 180}:
        raise ValueError("side extraction turns must align modules with +X")

    def finite(value):
        if isinstance(value, dict):
            return all(finite(v) for v in value.values())
        if isinstance(value, list):
            return all(finite(v) for v in value)
        return isinstance(value, str) or (
            not isinstance(value, bool) and math.isfinite(value)
        )

    if not finite(raw):
        raise ValueError("side coordinates must be finite")
    for key, value in raw.items():
        if isinstance(value, (int, float)) and value <= 0:
            raise ValueError(f"{key} must be positive")
    if raw["capture_rod_y_offset_mm"] <= 6:
        raise ValueError("horizontal rod must clear the journal above its center")
    return raw
