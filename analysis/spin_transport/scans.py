"""Reusable scan helpers for spin transport studies."""

from __future__ import annotations

import numpy as np

from .bmt import DEUTERON_ANOMALY, gamma_from_kinetic_energy
from .ensemble import gaussian_phase_average
from .polarimeter_response import CartesianAnalyzingPowers, four_sector_yields, sector_observables
from .spin1_density import axial_density_matrix, axial_tensor, tensor_components


def horizontal_bend_scan(p_tensor: float, bend_degrees: np.ndarray, kinetic_energy_mev: float = 380.0) -> dict[str, np.ndarray]:
    gamma = gamma_from_kinetic_energy(kinetic_energy_mev)
    delta = DEUTERON_ANOMALY * gamma * np.radians(bend_degrees)
    outputs = {"bend_deg": np.asarray(bend_degrees), "delta_deg": np.degrees(delta)}
    tensors = np.array([axial_tensor(p_tensor, np.array([np.sin(value), 0.0, np.cos(value)])) for value in delta])
    outputs.update({"pxx": tensors[:, 0, 0], "pyy": tensors[:, 1, 1], "pzz": tensors[:, 2, 2], "pxz": tensors[:, 0, 2]})
    return outputs


def phase_spread_scan(p_tensor: float, sigma_degrees: np.ndarray, mean_delta_rad: float = 0.0) -> dict[str, np.ndarray]:
    rho = axial_density_matrix(p_tensor, np.array([0.0, 0.0, 1.0]))
    tensors = np.array(
        [tensor_components(gaussian_phase_average(rho, np.array([0.0, 1.0, 0.0]), mean_delta_rad, np.radians(sigma))) for sigma in sigma_degrees]
    )
    return {"sigma_deg": np.asarray(sigma_degrees), "pxx": tensors[:, 0, 0], "pyy": tensors[:, 1, 1], "pzz": tensors[:, 2, 2], "pxz": tensors[:, 0, 2]}


def sector_angle_scan(p_tensor: float, delta_degrees: np.ndarray, analyzing: CartesianAnalyzingPowers, normalization: float = 100_000.0) -> dict[str, np.ndarray]:
    records: dict[str, list[float]] = {key: [] for key in ("L", "R", "U", "D", "L-R", "U-D", "LR-UD", "total")}
    for delta_deg in delta_degrees:
        axis = np.array([np.sin(np.radians(delta_deg)), 0.0, np.cos(np.radians(delta_deg))])
        yields = four_sector_yields(axial_tensor(p_tensor, axis), analyzing, normalization)
        observables = sector_observables(yields)
        for key in ("L", "R", "U", "D"):
            records[key].append(yields[key])
        for key, value in observables.items():
            records[key].append(value)
    return {"delta_deg": np.asarray(delta_degrees), **{key: np.asarray(value) for key, value in records.items()}}
