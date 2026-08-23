"""Four-sector d-p polarimeter response in the repository normalization."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from .spin1_density import axial_tensor
from .rotations import rotation_matrix


SECTOR_PHI_DEG = {"L": 0.0, "U": 90.0, "R": 180.0, "D": 270.0}


@dataclass(frozen=True)
class CartesianAnalyzingPowers:
    a_y: float
    a_xz: float
    a_xx_minus_yy: float
    a_zz: float


@dataclass(frozen=True)
class DetectorGeometry:
    theta_lab_deg: float
    radius_mm: float
    area_mm2: float = 400.0

    def center(self, phi_deg: float) -> np.ndarray:
        theta = np.radians(self.theta_lab_deg)
        phi = np.radians(phi_deg)
        return self.radius_mm * np.array([np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)])


@dataclass(frozen=True)
class PolarimeterChannel:
    name: str
    analyzing: CartesianAnalyzingPowers
    geometry: DetectorGeometry
    relative_scale: float = 1.0
    theta_cm_deg: float | None = None
    dtheta_cm_dtheta_lab: float = 0.0
    tensor_table_path: str | Path | None = None
    cross_section_table_path: str | Path | None = None


@lru_cache(maxsize=8)
def load_tensor_table(path: str | Path) -> np.ndarray:
    rows: list[list[float]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines()[1:]:
        fields = line.split()
        if not fields:
            continue
        rows.append([np.nan if value == "null" else float(value) for value in fields])
    return np.asarray(rows)


def analyzing_powers_from_table(theta_cm_deg: float, table_path: str | Path) -> CartesianAnalyzingPowers:
    table = load_tensor_table(table_path)

    def interpolate(column: int) -> float:
        finite = np.isfinite(table[:, column])
        return float(np.interp(theta_cm_deg, table[finite, 0], table[finite, column]))

    it11, t20, t21, t22 = interpolate(1), interpolate(3), interpolate(5), interpolate(7)
    # [EN] These Cartesian/spherical conversions reproduce the existing pzz and LR/UD count formulae / [CN] 这些笛卡尔/球张量换算严格复现现有 pzz 与 LR/UD 计数公式
    return CartesianAnalyzingPowers(
        a_y=2.0 * it11 / np.sqrt(3.0),
        a_xz=-np.sqrt(3.0) * t21,
        a_xx_minus_yy=2.0 * np.sqrt(3.0) * t22,
        a_zz=np.sqrt(2.0) * t20,
    )


@lru_cache(maxsize=8)
def load_cross_section_table(table_path: str | Path) -> np.ndarray:
    rows: list[tuple[float, float]] = []
    for line in Path(table_path).read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != 2:
            continue
        try:
            rows.append((float(fields[0]), float(fields[1])))
        except ValueError:
            continue
    return np.asarray(rows)


def differential_cross_section(theta_cm_deg: float, table_path: str | Path) -> float:
    table = load_cross_section_table(table_path)
    return float(np.interp(theta_cm_deg, table[:, 0], table[:, 1]))


def proton_cm_from_lab(theta_lab_rad: float, kinetic_energy_mev: float = 380.0, deuteron_mass_mev: float = 1875.612945, proton_mass_mev: float = 938.0) -> float:
    total_energy = deuteron_mass_mev + kinetic_energy_mev
    momentum = np.sqrt(total_energy**2 - deuteron_mass_mev**2)
    beta = momentum / (total_energy + proton_mass_mev)
    gamma = 1.0 / np.sqrt(1.0 - beta**2)
    deuteron_cm_momentum = -gamma * beta * total_energy + gamma * momentum
    proton_cm_energy = gamma * proton_mass_mev
    tangent = np.tan(theta_lab_rad)
    root = np.sqrt(1.0 + gamma**2 * tangent**2)
    arcsine = np.arcsin(tangent * gamma * beta * proton_cm_energy / (deuteron_cm_momentum * root))
    return float(np.pi - (np.arctan(gamma * tangent) + arcsine))


def proton_cm_slope(theta_lab_rad: float, step_rad: float = 1.0e-6) -> float:
    return (proton_cm_from_lab(theta_lab_rad + step_rad) - proton_cm_from_lab(theta_lab_rad - step_rad)) / (2.0 * step_rad)


def cross_section_factor(
    tensor: np.ndarray,
    phi_rad: float,
    analyzing: CartesianAnalyzingPowers,
    vector: np.ndarray | None = None,
) -> float:
    vector = np.zeros(3) if vector is None else np.asarray(vector, dtype=float)
    pxx, pyy, pzz = tensor[0, 0], tensor[1, 1], tensor[2, 2]
    pxy, pxz, pyz = tensor[0, 1], tensor[0, 2], tensor[1, 2]
    return float(
        1.0
        + 1.5 * (vector[0] * np.sin(phi_rad) + vector[1] * np.cos(phi_rad)) * analyzing.a_y
        + (2.0 / 3.0) * (pxz * np.cos(phi_rad) - pyz * np.sin(phi_rad)) * analyzing.a_xz
        + (1.0 / 6.0) * ((pxx - pyy) * np.cos(2.0 * phi_rad) - 2.0 * pxy * np.sin(2.0 * phi_rad)) * analyzing.a_xx_minus_yy
        + 0.5 * pzz * analyzing.a_zz
    )


def local_scattering_coordinates(
    detector_center: np.ndarray,
    beam_position_mm: np.ndarray,
    alpha_x_rad: float,
    alpha_y_rad: float,
) -> tuple[float, float, float]:
    z_axis = np.array([alpha_x_rad, alpha_y_rad, 1.0])
    z_axis /= np.linalg.norm(z_axis)
    reference_y = np.array([0.0, 1.0, 0.0])
    x_axis = np.cross(reference_y, z_axis)
    x_axis /= np.linalg.norm(x_axis)
    y_axis = np.cross(z_axis, x_axis)
    ray = np.asarray(detector_center) - np.asarray(beam_position_mm)
    distance = np.linalg.norm(ray)
    direction = ray / distance
    theta = np.arccos(np.clip(np.dot(direction, z_axis), -1.0, 1.0))
    phi = np.arctan2(np.dot(direction, y_axis), np.dot(direction, x_axis))
    return float(theta), float(phi), float(distance)


def four_sector_yields(
    tensor: np.ndarray,
    analyzing: CartesianAnalyzingPowers,
    normalization: float = 100_000.0,
    geometry: DetectorGeometry | None = None,
    beam_position_mm: tuple[float, float] = (0.0, 0.0),
    beam_angle_mrad: tuple[float, float] = (0.0, 0.0),
) -> dict[str, float]:
    yields: dict[str, float] = {}
    for sector, phi_deg in SECTOR_PHI_DEG.items():
        phi_rad = np.radians(phi_deg)
        geometric_scale = 1.0
        if geometry is not None:
            center = geometry.center(phi_deg)
            _, phi_rad, distance = local_scattering_coordinates(
                center,
                np.array([beam_position_mm[0], beam_position_mm[1], 0.0]),
                beam_angle_mrad[0] * 1.0e-3,
                beam_angle_mrad[1] * 1.0e-3,
            )
            geometric_scale = (geometry.radius_mm / distance) ** 2
        yields[sector] = normalization * geometric_scale * cross_section_factor(tensor, phi_rad, analyzing)
    return yields


def multi_channel_yields(
    tensor: np.ndarray,
    channels: list[PolarimeterChannel],
    normalization: float = 100_000.0,
    beam_position_mm: tuple[float, float] = (0.0, 0.0),
    beam_angle_mrad: tuple[float, float] = (0.0, 0.0),
) -> dict[str, float]:
    output: dict[str, float] = {}
    for channel in channels:
        for sector, phi_deg in SECTOR_PHI_DEG.items():
            center = channel.geometry.center(phi_deg)
            theta_rad, phi_rad, distance = local_scattering_coordinates(
                center,
                np.array([beam_position_mm[0], beam_position_mm[1], 0.0]),
                beam_angle_mrad[0] * 1.0e-3,
                beam_angle_mrad[1] * 1.0e-3,
            )
            analyzing = channel.analyzing
            cross_section_scale = 1.0
            if channel.theta_cm_deg is not None:
                theta_cm = channel.theta_cm_deg + channel.dtheta_cm_dtheta_lab * (np.degrees(theta_rad) - channel.geometry.theta_lab_deg)
                if channel.tensor_table_path is not None:
                    analyzing = analyzing_powers_from_table(theta_cm, channel.tensor_table_path)
                if channel.cross_section_table_path is not None:
                    cross_section_scale = differential_cross_section(theta_cm, channel.cross_section_table_path) / differential_cross_section(channel.theta_cm_deg, channel.cross_section_table_path)
            geometric_scale = (channel.geometry.radius_mm / distance) ** 2
            output[f"{channel.name}:{sector}"] = normalization * channel.relative_scale * geometric_scale * cross_section_scale * cross_section_factor(tensor, phi_rad, analyzing)
    return output


def sector_observables(yields: dict[str, float]) -> dict[str, float]:
    left, right, up, down = yields["L"], yields["R"], yields["U"], yields["D"]
    total = left + right + up + down
    return {
        "L-R": (left - right) / total,
        "U-D": (up - down) / total,
        "LR-UD": (left + right - up - down) / total,
        "total": total,
    }


def fit_axial_z_tensor(
    observed: dict[str, float],
    analyzing: CartesianAnalyzingPowers,
    p_bounds: tuple[float, float] = (-2.0, 1.0),
    delta_bounds_deg: tuple[float, float] = (-45.0, 45.0),
    p_steps: int = 301,
    delta_steps: int = 361,
    geometry: DetectorGeometry | None = None,
    assumed_beam_position_mm: tuple[float, float] = (0.0, 0.0),
    assumed_beam_angle_mrad: tuple[float, float] = (0.0, 0.0),
) -> dict[str, float]:
    keys = ("L", "U", "R", "D")
    data = np.array([observed[key] for key in keys])
    try:
        from scipy.optimize import minimize

        def objective(parameters: np.ndarray) -> float:
            p_tensor, delta_deg = parameters
            axis = np.array([np.sin(np.radians(delta_deg)), 0.0, np.cos(np.radians(delta_deg))])
            model = four_sector_yields(
                axial_tensor(p_tensor, axis), analyzing, 1.0, geometry=geometry,
                beam_position_mm=assumed_beam_position_mm, beam_angle_mrad=assumed_beam_angle_mrad,
            )
            shape = np.array([model[key] for key in keys])
            normalization = data.sum() / shape.sum()
            expected = np.maximum(normalization * shape, 1.0e-12)
            positive = data > 0.0
            return float(2.0 * np.sum(expected - data + np.where(positive, data * np.log(data / expected), 0.0)))

        # [EN] A bounded global seed avoids the pT-delta mirror ambiguity before local likelihood refinement / [CN] 有界全局初值在局域似然细化前避免 pT-delta 镜像歧义
        seeds = [np.array([p_value, delta_value]) for p_value in np.linspace(*p_bounds, 13) for delta_value in np.linspace(*delta_bounds_deg, 25)]
        seed = min(seeds, key=objective)
        fitted = minimize(objective, seed, method="L-BFGS-B", bounds=[p_bounds, delta_bounds_deg], options={"ftol": 1.0e-14, "gtol": 1.0e-10})
        p_tensor, delta_deg = fitted.x
        axis = np.array([np.sin(np.radians(delta_deg)), 0.0, np.cos(np.radians(delta_deg))])
        shape_map = four_sector_yields(axial_tensor(p_tensor, axis), analyzing, 1.0, geometry=geometry)
        normalization = data.sum() / sum(shape_map.values())
        return {"deviance": float(fitted.fun), "p_tensor": float(p_tensor), "delta_deg": float(delta_deg), "normalization": float(normalization)}
    except ImportError:
        pass
    best = {"deviance": np.inf, "p_tensor": np.nan, "delta_deg": np.nan, "normalization": np.nan}
    for p_tensor in np.linspace(*p_bounds, p_steps):
        for delta_deg in np.linspace(*delta_bounds_deg, delta_steps):
            axis = np.array([np.sin(np.radians(delta_deg)), 0.0, np.cos(np.radians(delta_deg))])
            model_unit = four_sector_yields(
                axial_tensor(p_tensor, axis),
                analyzing,
                normalization=1.0,
                geometry=geometry,
                beam_position_mm=assumed_beam_position_mm,
                beam_angle_mrad=assumed_beam_angle_mrad,
            )
            shape = np.array([model_unit[key] for key in keys])
            normalization = data.sum() / shape.sum()
            expected = np.maximum(normalization * shape, 1.0e-12)
            positive = data > 0.0
            deviance = 2.0 * np.sum(expected - data + np.where(positive, data * np.log(data / expected), 0.0))
            if deviance < best["deviance"]:
                best = {"deviance": float(deviance), "p_tensor": float(p_tensor), "delta_deg": float(delta_deg), "normalization": float(normalization)}
    return best


def fit_axial_tensor(
    observed: dict[str, float],
    analyzing: CartesianAnalyzingPowers,
    base_axis: np.ndarray,
    rotation_axis: np.ndarray,
    p_bounds: tuple[float, float] = (-2.0, 1.0),
    delta_bounds_deg: tuple[float, float] = (-45.0, 45.0),
    p_steps: int = 151,
    delta_steps: int = 241,
    geometry: DetectorGeometry | None = None,
) -> dict[str, float]:
    keys = ("L", "U", "R", "D")
    data = np.array([observed[key] for key in keys])
    base_axis = np.asarray(base_axis, dtype=float)
    base_axis /= np.linalg.norm(base_axis)
    try:
        from scipy.optimize import minimize

        def objective(parameters: np.ndarray) -> float:
            p_tensor, delta_deg = parameters
            axis = rotation_matrix(rotation_axis, np.radians(delta_deg)) @ base_axis
            model = four_sector_yields(axial_tensor(p_tensor, axis), analyzing, 1.0, geometry=geometry)
            shape = np.array([model[key] for key in keys])
            normalization = data.sum() / shape.sum()
            expected = np.maximum(normalization * shape, 1.0e-12)
            positive = data > 0.0
            return float(2.0 * np.sum(expected - data + np.where(positive, data * np.log(data / expected), 0.0)))

        seeds = [np.array([p_value, delta_value]) for p_value in np.linspace(*p_bounds, 13) for delta_value in np.linspace(*delta_bounds_deg, 25)]
        seed = min(seeds, key=objective)
        fitted = minimize(objective, seed, method="L-BFGS-B", bounds=[p_bounds, delta_bounds_deg], options={"ftol": 1.0e-14, "gtol": 1.0e-10})
        p_tensor, delta_deg = fitted.x
        axis = rotation_matrix(rotation_axis, np.radians(delta_deg)) @ base_axis
        shape_map = four_sector_yields(axial_tensor(p_tensor, axis), analyzing, 1.0, geometry=geometry)
        normalization = data.sum() / sum(shape_map.values())
        return {"deviance": float(fitted.fun), "p_tensor": float(p_tensor), "delta_deg": float(delta_deg), "normalization": float(normalization)}
    except ImportError:
        pass
    best = {"deviance": np.inf, "p_tensor": np.nan, "delta_deg": np.nan, "normalization": np.nan}
    for p_tensor in np.linspace(*p_bounds, p_steps):
        for delta_deg in np.linspace(*delta_bounds_deg, delta_steps):
            axis = rotation_matrix(rotation_axis, np.radians(delta_deg)) @ base_axis
            model = four_sector_yields(axial_tensor(p_tensor, axis), analyzing, 1.0, geometry=geometry)
            shape = np.array([model[key] for key in keys])
            normalization = data.sum() / shape.sum()
            expected = np.maximum(normalization * shape, 1.0e-12)
            positive = data > 0.0
            deviance = 2.0 * np.sum(expected - data + np.where(positive, data * np.log(data / expected), 0.0))
            if deviance < best["deviance"]:
                best = {"deviance": float(deviance), "p_tensor": float(p_tensor), "delta_deg": float(delta_deg), "normalization": float(normalization)}
    return best


def fit_axial_multi_channel(
    observed: dict[str, float],
    channels: list[PolarimeterChannel],
    base_axis: np.ndarray,
    rotation_axis: np.ndarray,
    p_bounds: tuple[float, float] = (-2.0, 1.0),
    delta_bounds_deg: tuple[float, float] = (-45.0, 45.0),
) -> dict[str, float]:
    from scipy.optimize import minimize

    keys = tuple(f"{channel.name}:{sector}" for channel in channels for sector in ("L", "U", "R", "D"))
    data = np.array([observed[key] for key in keys])
    base_axis = np.asarray(base_axis, dtype=float) / np.linalg.norm(base_axis)

    def objective(parameters: np.ndarray) -> float:
        p_tensor, delta_deg = parameters
        axis = rotation_matrix(rotation_axis, np.radians(delta_deg)) @ base_axis
        model = multi_channel_yields(axial_tensor(p_tensor, axis), channels, 1.0)
        shape = np.array([model[key] for key in keys])
        normalization = data.sum() / shape.sum()
        expected = np.maximum(normalization * shape, 1.0e-12)
        positive = data > 0.0
        return float(2.0 * np.sum(expected - data + np.where(positive, data * np.log(data / expected), 0.0)))

    seeds = [np.array([p_value, delta_value]) for p_value in np.linspace(*p_bounds, 13) for delta_value in np.linspace(*delta_bounds_deg, 25)]
    seed = min(seeds, key=objective)
    fitted = minimize(objective, seed, method="L-BFGS-B", bounds=[p_bounds, delta_bounds_deg], options={"ftol": 1.0e-14, "gtol": 1.0e-10})
    p_tensor, delta_deg = fitted.x
    axis = rotation_matrix(rotation_axis, np.radians(delta_deg)) @ base_axis
    shape = multi_channel_yields(axial_tensor(p_tensor, axis), channels, 1.0)
    normalization = data.sum() / sum(shape.values())
    return {"deviance": float(fitted.fun), "p_tensor": float(p_tensor), "delta_deg": float(delta_deg), "normalization": float(normalization)}


def fisher_resolution_axial_z(
    p_tensor: float,
    delta_rad: float,
    analyzing: CartesianAnalyzingPowers,
    normalization: float,
) -> tuple[float, float]:
    parameters = np.array([p_tensor, delta_rad, normalization], dtype=float)

    def model(values: np.ndarray) -> np.ndarray:
        p_value, delta_value, norm_value = values
        axis = np.array([np.sin(delta_value), 0.0, np.cos(delta_value)])
        yields = four_sector_yields(axial_tensor(p_value, axis), analyzing, norm_value)
        return np.array([yields[key] for key in ("L", "U", "R", "D")])

    means = model(parameters)
    jacobian = np.empty((4, 3))
    steps = np.array([1.0e-5, 1.0e-6, max(1.0e-3, normalization * 1.0e-6)])
    for column, step in enumerate(steps):
        plus, minus = parameters.copy(), parameters.copy()
        plus[column] += step
        minus[column] -= step
        jacobian[:, column] = (model(plus) - model(minus)) / (2.0 * step)
    fisher = jacobian.T @ np.diag(1.0 / means) @ jacobian
    covariance = np.linalg.pinv(fisher)
    return float(np.sqrt(covariance[0, 0])), float(np.sqrt(covariance[1, 1]))


def fisher_resolution_multi_channel(
    p_tensor: float,
    delta_rad: float,
    channels: list[PolarimeterChannel],
    normalization: float,
) -> tuple[float, float, float]:
    parameters = np.array([p_tensor, delta_rad, normalization], dtype=float)
    keys = tuple(f"{channel.name}:{sector}" for channel in channels for sector in ("L", "U", "R", "D"))

    def model(values: np.ndarray) -> np.ndarray:
        p_value, delta_value, norm_value = values
        axis = np.array([np.sin(delta_value), 0.0, np.cos(delta_value)])
        yields = multi_channel_yields(axial_tensor(p_value, axis), channels, norm_value)
        return np.array([yields[key] for key in keys])

    means = model(parameters)
    jacobian = np.empty((len(keys), 3))
    steps = np.array([1.0e-5, 1.0e-6, max(1.0e-3, normalization * 1.0e-6)])
    for column, step in enumerate(steps):
        plus, minus = parameters.copy(), parameters.copy()
        plus[column] += step
        minus[column] -= step
        jacobian[:, column] = (model(plus) - model(minus)) / (2.0 * step)
    fisher = jacobian.T @ np.diag(1.0 / means) @ jacobian
    covariance = np.linalg.inv(fisher)
    return float(np.sqrt(covariance[0, 0])), float(np.sqrt(covariance[1, 1])), float(np.linalg.cond(fisher))
