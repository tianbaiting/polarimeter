"""Ensemble averaging of coherently transported spin-1 states."""

from __future__ import annotations

import numpy as np

from .spin1_density import rotate_density


def gaussian_phase_average(
    rho_initial: np.ndarray,
    axis: np.ndarray,
    mean_angle_rad: float,
    sigma_angle_rad: float,
    quadrature_points: int = 81,
) -> np.ndarray:
    if sigma_angle_rad == 0.0:
        return rotate_density(rho_initial, axis, mean_angle_rad)
    nodes, weights = np.polynomial.hermite.hermgauss(quadrature_points)
    angles = mean_angle_rad + np.sqrt(2.0) * sigma_angle_rad * nodes
    rho_average = np.zeros((3, 3), dtype=complex)
    # [EN] Gauss-Hermite integration averages phase-space-dependent unitaries without Monte Carlo noise / [CN] Gauss-Hermite 积分对相空间相关的幺正变换做无蒙特卡洛噪声的平均
    for angle, weight in zip(angles, weights, strict=True):
        rho_average += weight * rotate_density(rho_initial, axis, float(angle))
    return rho_average / np.sqrt(np.pi)


def analytic_gaussian_axial_z(p_tensor: float, mean_angle_rad: float, sigma_angle_rad: float) -> np.ndarray:
    second_harmonic = np.exp(-2.0 * sigma_angle_rad**2)
    sin_two = np.sin(2.0 * mean_angle_rad) * second_harmonic
    cos_two = np.cos(2.0 * mean_angle_rad) * second_harmonic
    return np.array(
        [
            [p_tensor * (0.25 - 0.75 * cos_two), 0.0, 0.75 * p_tensor * sin_two],
            [0.0, -0.5 * p_tensor, 0.0],
            [0.75 * p_tensor * sin_two, 0.0, p_tensor * (0.25 + 0.75 * cos_two)],
        ]
    )
