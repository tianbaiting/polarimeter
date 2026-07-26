#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class RangeModel:
    key: str
    label: str
    energy_column: int
    range_column: int


@dataclass(frozen=True)
class RangeTable:
    model: RangeModel
    energy_mev_per_u: np.ndarray
    range_um: np.ndarray


RANGE_MODELS: tuple[RangeModel, ...] = (
    RangeModel("hubert_1990", "Hubert et al. (1990)", 0, 1),
    RangeModel("ziegler_low_energy", "Ziegler low-energy", 2, 3),
    RangeModel("atima_1_2_ls", "ATIMA 1.2 LS", 4, 5),
    RangeModel("atima_1_2_no_ls", "ATIMA 1.2 without LS correction", 6, 7),
    RangeModel("atima_1_4_mean_charge", "ATIMA 1.4 improved mean charge", 8, 9),
)
RANGE_MODELS_BY_KEY = {model.key: model for model in RANGE_MODELS}
DEFAULT_MODEL_KEY = "atima_1_2_ls"


def available_model_keys() -> tuple[str, ...]:
    return tuple(model.key for model in RANGE_MODELS)


def load_range_table(path: Path, model_key: str = DEFAULT_MODEL_KEY) -> RangeTable:
    try:
        model = RANGE_MODELS_BY_KEY[model_key]
    except KeyError as error:
        supported = ", ".join(available_model_keys())
        raise ValueError(f"Unsupported LISE++ range model '{model_key}'; expected one of: {supported}") from error

    data = np.loadtxt(path, skiprows=3)
    if data.ndim != 2 or data.shape[1] <= model.range_column:
        raise ValueError(f"LISE++ table does not contain the columns required by {model.label}: {path}")

    energy = np.asarray(data[:, model.energy_column], dtype=float)
    particle_range = np.asarray(data[:, model.range_column], dtype=float)
    if np.any(~np.isfinite(energy)) or np.any(~np.isfinite(particle_range)):
        raise ValueError(f"LISE++ table contains non-finite values: {path}")
    if np.any(np.diff(energy) <= 0.0):
        raise ValueError(f"LISE++ energy grid must be strictly increasing: {path}")
    if np.any(np.diff(particle_range) < 0.0):
        raise ValueError(f"LISE++ range column must be monotonic: {path}")

    return RangeTable(model=model, energy_mev_per_u=energy, range_um=particle_range)


def particle_range_um(
    kinetic_energy_per_u_mev: np.ndarray | float,
    table: RangeTable,
) -> np.ndarray:
    kinetic_energy = np.asarray(kinetic_energy_per_u_mev, dtype=float)
    finite_mask = np.isfinite(kinetic_energy)
    if np.any(kinetic_energy[finite_mask] < 0.0):
        raise ValueError("Finite kinetic-energy samples must be non-negative")
    if np.any(kinetic_energy[finite_mask] > table.energy_mev_per_u[-1]):
        raise ValueError(
            f"Kinetic energy exceeds the LISE++ table limit of {table.energy_mev_per_u[-1]:.6g} MeV/u",
        )

    interpolation_energy = np.where(finite_mask, kinetic_energy, 0.0)
    interpolated = np.interp(
        interpolation_energy,
        table.energy_mev_per_u,
        table.range_um,
    )
    positive_range = np.where(interpolation_energy > 0.0, interpolated, 0.0)
    return np.where(finite_mask, positive_range, np.nan)


def energy_loss_mev(
    mass_number: int,
    kinetic_energy_per_u_mev: np.ndarray | float,
    thickness_um: float,
    table: RangeTable,
) -> np.ndarray:
    if mass_number <= 0:
        raise ValueError("Mass number must be positive")
    if not np.isfinite(thickness_um) or thickness_um < 0.0:
        raise ValueError("Scintillator thickness must be finite and non-negative")

    kinetic_energy = np.asarray(kinetic_energy_per_u_mev, dtype=float)
    total_kinetic_energy = kinetic_energy * float(mass_number)
    initial_range = particle_range_um(kinetic_energy, table)
    residual_range = np.maximum(initial_range - thickness_um, 0.0)

    # [EN] Remove repeated zero-range samples before inverse interpolation so stopped particles map exactly to zero residual energy / [CN] 反向插值前去除重复的零射程点，使完全停止的粒子严格对应零剩余能量
    unique_mask = np.concatenate(
        (np.array([True]), np.diff(table.range_um) > 0.0),
    )
    inverse_range = table.range_um[unique_mask]
    inverse_energy = table.energy_mev_per_u[unique_mask]
    residual_energy_per_u = np.interp(
        residual_range,
        inverse_range,
        inverse_energy,
    )
    residual_energy_per_u = np.where(residual_range > 0.0, residual_energy_per_u, 0.0)

    # [EN] Range subtraction is the continuous-slowing-down approximation used by the original LISE++ workflow / [CN] 射程相减采用原 LISE++ 工作流中的连续慢化近似
    deposited = total_kinetic_energy - residual_energy_per_u * float(mass_number)
    return np.clip(deposited, 0.0, total_kinetic_energy)
