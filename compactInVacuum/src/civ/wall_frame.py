from __future__ import annotations

from dataclasses import replace
import FreeCAD as App


def wall_angle(wall):
    return {"positive_y_top": 0, "positive_x_side": -90, "negative_x_side": 90}[wall]


def wall_rotation(wall):
    return App.Rotation(App.Vector(0, 0, 1), wall_angle(wall))


def orient(shape, wall):
    result = shape.copy()
    result.rotate(App.Vector(), App.Vector(0, 0, 1), wall_angle(wall))
    return result


def access_local_spec(access):
    s = access.selected
    return replace(
        s,
        center_x_mm=(
            s.center_x_mm
            if access.wall == "positive_y_top"
            else (-s.center_y_mm if access.wall == "positive_x_side" else s.center_y_mm)
        ),
    )


def wall_half_size(cfg, wall):
    return (
        cfg.vessel.inner_size_y_mm
        if wall == "positive_y_top"
        else cfg.vessel.inner_size_x_mm
    ) / 2


def port_frame(cfg, port):
    if port.wall == "positive_y_top":
        from .feedthrough import service_wall_y_mm

        return (
            App.Vector(
                port.center_x_mm,
                service_wall_y_mm(cfg, port.center_x_mm),
                port.center_z_mm,
            ),
            App.Vector(0, 1, 0),
            App.Vector(1, 0, 0),
        )
    if cfg.vessel.cross_section != "square":
        raise ValueError("side feedthroughs currently require a square chamber")
    rotation = wall_rotation(port.wall)
    tangent = -port.center_y_mm if port.wall == "positive_x_side" else port.center_y_mm
    # [EN] Wall-normal rotation changes service geometry without rotating the target or frozen detector coordinates. / [CN] 壁面法向变换只改变服务接口几何，不旋转转靶机构或已冻结的探测器坐标。
    return (
        rotation.multVec(
            App.Vector(tangent, wall_half_size(cfg, port.wall), port.center_z_mm)
        ),
        rotation.multVec(App.Vector(0, 1, 0)),
        rotation.multVec(App.Vector(1, 0, 0)),
    )
