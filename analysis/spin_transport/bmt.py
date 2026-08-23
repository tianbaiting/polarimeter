"""Thomas-BMT transport for deuterons."""

from __future__ import annotations

import numpy as np


DEUTERON_MASS_MEV = 1875.61294500
DEUTERON_PROTON_MASS_RATIO = 1.9990075012699
DEUTERON_MAGNETIC_MOMENT_NUCLEAR_MAGNETONS = 0.8574382335
# [EN] Convert the CODATA nuclear g-factor to the BMT g defined with the particle mass / [CN] 将 CODATA 核 g 因子换算为以粒子质量定义的 BMT g 因子
DEUTERON_BMT_G = DEUTERON_MAGNETIC_MOMENT_NUCLEAR_MAGNETONS * DEUTERON_PROTON_MASS_RATIO
DEUTERON_ANOMALY = 0.5 * (DEUTERON_BMT_G - 2.0)


def gamma_from_kinetic_energy(kinetic_energy_mev: float, mass_mev: float = DEUTERON_MASS_MEV) -> float:
    return 1.0 + kinetic_energy_mev / mass_mev


def beta_from_gamma(gamma: float) -> float:
    return float(np.sqrt(1.0 - 1.0 / gamma**2))


def bmt_angular_velocity(
    charge_over_mass: float,
    gamma: float,
    beta_vector: np.ndarray,
    magnetic_field: np.ndarray,
    electric_field: np.ndarray | None = None,
    anomaly: float = DEUTERON_ANOMALY,
    speed_of_light: float = 299_792_458.0,
) -> np.ndarray:
    beta_vector = np.asarray(beta_vector, dtype=float)
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    electric_field = np.zeros(3) if electric_field is None else np.asarray(electric_field, dtype=float)
    # [EN] Omega is defined by ds/dt=Omega cross s in laboratory time / [CN] Omega 按实验室时间中的 ds/dt=Omega 叉乘 s 定义
    bracket = (
        (anomaly + 1.0 / gamma) * magnetic_field
        - anomaly * gamma / (gamma + 1.0) * beta_vector * np.dot(beta_vector, magnetic_field)
        - (anomaly + 1.0 / (gamma + 1.0)) * np.cross(beta_vector, electric_field) / speed_of_light
    )
    return -charge_over_mass * bracket


def ideal_dipole_spin_angles(orbit_angle_rad: float, gamma: float, anomaly: float = DEUTERON_ANOMALY) -> tuple[float, float]:
    spin_lab = (1.0 + anomaly * gamma) * orbit_angle_rad
    relative = anomaly * gamma * orbit_angle_rad
    return spin_lab, relative


def relative_spin_per_orbit(gamma: float, anomaly: float = DEUTERON_ANOMALY) -> float:
    return anomaly * gamma
