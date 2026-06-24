from __future__ import annotations

import json
import math
from pathlib import Path

from .components import build_end_modules, build_vessel_body
from .config import CIVConfig, end_module_has_groove
from .layout import DetectorPlacement, front_face_center, norm


def _scattering_angle_deg(direction) -> float:
    length = norm(direction)
    if length <= 0.0:
        return 0.0
    cos_theta = max(-1.0, min(1.0, direction.z / length))
    return math.degrees(math.acos(cos_theta))


def _result(name: str, passed: bool, **payload: object) -> dict[str, object]:
    result: dict[str, object] = {
        "name": name,
        "status": "pass" if passed else "fail",
    }
    result.update(payload)
    return result


def _end_module_type_semantics_ok(standard: str, groove_depth_mm: float) -> bool:
    if end_module_has_groove(standard):
        return groove_depth_mm > 0.0
    return groove_depth_mm <= 0.0


def _vacuum_boundary_check(cfg: CIVConfig) -> dict[str, object]:
    vessel_body = build_vessel_body(cfg)
    front_module, rear_module = build_end_modules(cfg)
    vacuum_boundary = vessel_body.fuse(front_module).fuse(rear_module)
    solid_count = len(vacuum_boundary.Solids)
    shell_count = sum(len(solid.Shells) for solid in vacuum_boundary.Solids)
    closed_shells = all(shell.isClosed() for solid in vacuum_boundary.Solids for shell in solid.Shells)
    passed = (
        not vacuum_boundary.isNull()
        and vacuum_boundary.isValid()
        and solid_count == 1
        and closed_shells
        and vacuum_boundary.Volume > 0.0
    )
    return _result(
        "vacuum_boundary_complete",
        passed,
        detail=(
            f"solids={solid_count}, shells={shell_count}, "
            f"closed={closed_shells}, volume={vacuum_boundary.Volume:.3f}"
        ),
    )


def validate_assembly(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
    strict: bool,
    output_path: str | Path | None = None,
) -> dict[str, object]:
    channel_by_name = {channel.name: channel for channel in cfg.channels}
    checks: list[dict[str, object]] = []

    for placement in placements:
        channel = channel_by_name[placement.channel_name]
        actual_angle = _scattering_angle_deg(placement.direction)
        actual_radius = norm(front_face_center(placement))

        angle_delta = abs(actual_angle - channel.angle_deg)
        radius_delta = abs(actual_radius - channel.radius_mm)

        checks.append(
            _result(
                f"{placement.tag}.angle_deg",
                angle_delta <= cfg.validation.angle_tolerance_deg,
                value=actual_angle,
                expected=channel.angle_deg,
                tolerance=cfg.validation.angle_tolerance_deg,
            )
        )
        checks.append(
            _result(
                f"{placement.tag}.radius_mm",
                radius_delta <= cfg.validation.radius_tolerance_mm,
                value=actual_radius,
                expected=channel.radius_mm,
                tolerance=cfg.validation.radius_tolerance_mm,
            )
        )

    square_contract_ok = (
        cfg.vessel.cross_section == "square"
        and math.isclose(cfg.vessel.inner_size_x_mm, cfg.vessel.inner_size_y_mm, rel_tol=0.0, abs_tol=1e-9)
    )
    checks.append(
        _result(
            "vessel_cross_section_contract",
            square_contract_ok,
            detail=(
                f"cross_section={cfg.vessel.cross_section}, "
                f"inner_size_x_mm={cfg.vessel.inner_size_x_mm:.3f}, "
                f"inner_size_y_mm={cfg.vessel.inner_size_y_mm:.3f}"
            ),
        )
    )

    front_module = cfg.vessel.end_modules.front
    rear_module = cfg.vessel.end_modules.rear
    standards_ok = (
        front_module.standard.upper() == cfg.vessel.contract.front_standard.upper()
        and rear_module.standard.upper() == cfg.vessel.contract.rear_standard.upper()
    )
    checks.append(
        _result(
            "end_module_standard",
            standards_ok,
            detail=f"front={front_module.standard}, rear={rear_module.standard}",
        )
    )

    type_semantics_ok = _end_module_type_semantics_ok(
        front_module.standard,
        front_module.oring_groove_depth_mm,
    ) and _end_module_type_semantics_ok(
        rear_module.standard,
        rear_module.oring_groove_depth_mm,
    )
    checks.append(
        _result(
            "end_module_type_semantics",
            type_semantics_ok,
            detail=(
                f"front={front_module.standard}[groove_depth={front_module.oring_groove_depth_mm:.3f}], "
                f"rear={rear_module.standard}[groove_depth={rear_module.oring_groove_depth_mm:.3f}]"
            ),
        )
    )

    pipe_stub_ok = True
    stub_parts: list[str] = []
    for side_name, module in (("front", front_module), ("rear", rear_module)):
        side_ok = (
            module.pipe_length_mm > 0.0
            and module.pipe_inner_diameter_mm >= cfg.vessel.beam_bore_diameter_mm
            and module.pipe_outer_diameter_mm <= module.module_inner_diameter_mm
        )
        pipe_stub_ok = pipe_stub_ok and side_ok
        stub_parts.append(
            f"{side_name}[std={module.standard},pipe=({module.pipe_outer_diameter_mm:.1f},{module.pipe_inner_diameter_mm:.1f},{module.pipe_length_mm:.1f})]"
        )
    checks.append(
        _result(
            "welded_pipe_stub_to_standard_flange",
            pipe_stub_ok,
            detail="; ".join(stub_parts),
        )
    )

    checks.append(_vacuum_boundary_check(cfg))

    report = {
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "checks": checks,
    }

    _ = strict

    if output_path is not None:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return report
