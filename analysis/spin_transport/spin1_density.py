"""Spin-1 density matrices in the Cartesian convention used by this repository."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


COMPONENT_KEYS = ("xx", "yy", "zz", "xy", "xz", "yz")


def spin_matrices() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    root_two = np.sqrt(2.0)
    sx = np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=complex) / root_two
    sy = np.array([[0.0, -1.0j, 0.0], [1.0j, 0.0, -1.0j], [0.0, 1.0j, 0.0]], dtype=complex) / root_two
    sz = np.diag([1.0, 0.0, -1.0]).astype(complex)
    return sx, sy, sz


def tensor_operators() -> dict[str, np.ndarray]:
    spins = spin_matrices()
    identity = np.eye(3, dtype=complex)
    operators: dict[str, np.ndarray] = {}
    labels = "xyz"
    for i, first in enumerate(spins):
        for j in range(i, 3):
            second = spins[j]
            # [EN] This Ohlsen operator gives p_aa=N(+1)+N(-1)-2N(0), matching the existing polarimeter note / [CN] 此 Ohlsen 算符给出 p_aa=N(+1)+N(-1)-2N(0)，与现有极化仪文档一致
            operator = 1.5 * (first @ second + second @ first)
            if i == j:
                operator -= 2.0 * identity
            operators[labels[i] + labels[j]] = operator
    return operators


def density_from_components(
    vector: np.ndarray | None = None,
    tensor: np.ndarray | None = None,
) -> np.ndarray:
    vector = np.zeros(3) if vector is None else np.asarray(vector, dtype=float)
    tensor = np.zeros((3, 3)) if tensor is None else np.asarray(tensor, dtype=float)
    if vector.shape != (3,) or tensor.shape != (3, 3):
        raise ValueError("Vector and tensor must have shapes (3,) and (3,3)")
    if not np.allclose(tensor, tensor.T, atol=1.0e-12):
        raise ValueError("Tensor polarization must be symmetric")
    if not np.isclose(np.trace(tensor), 0.0, atol=1.0e-12):
        raise ValueError("Tensor polarization must be traceless")

    sx, sy, sz = spin_matrices()
    operators = tensor_operators()
    rho = np.eye(3, dtype=complex) / 3.0
    for value, operator in zip(vector, (sx, sy, sz), strict=True):
        rho += 0.5 * value * operator
    rho += (tensor[0, 0] * operators["xx"] + tensor[1, 1] * operators["yy"] + tensor[2, 2] * operators["zz"]) / 9.0
    rho += 2.0 * (tensor[0, 1] * operators["xy"] + tensor[0, 2] * operators["xz"] + tensor[1, 2] * operators["yz"]) / 9.0
    return rho


def axial_tensor(p_tensor: float, axis: np.ndarray) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    # [EN] The eigenvalues (-pT/2,-pT/2,pT) separate tensor magnitude from its principal-axis direction / [CN] 本征值 (-pT/2,-pT/2,pT) 将张量幅度与主轴方向分离
    return 1.5 * p_tensor * np.outer(axis, axis) - 0.5 * p_tensor * np.eye(3)


def axial_density_matrix(p_tensor: float, axis: np.ndarray, vector_along_axis: float = 0.0) -> np.ndarray:
    if p_tensor < -2.0 - 1.0e-12 or p_tensor > 1.0 + 1.0e-12:
        raise ValueError("Repository tensor convention requires -2 <= pT <= 1")
    axis = np.asarray(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    rho = density_from_components(vector_along_axis * axis, axial_tensor(p_tensor, axis))
    if np.min(np.linalg.eigvalsh(rho)) < -1.0e-12:
        raise ValueError("Vector/tensor combination is not a physical density matrix")
    return rho


def vector_components(rho: np.ndarray) -> np.ndarray:
    return np.array([np.trace(rho @ operator).real for operator in spin_matrices()])


def tensor_components(rho: np.ndarray) -> np.ndarray:
    operators = tensor_operators()
    values = {key: float(np.trace(rho @ operator).real) for key, operator in operators.items()}
    return np.array(
        [
            [values["xx"], values["xy"], values["xz"]],
            [values["xy"], values["yy"], values["yz"]],
            [values["xz"], values["yz"], values["zz"]],
        ]
    )


def rotate_density(rho: np.ndarray, axis: np.ndarray, angle_rad: float) -> np.ndarray:
    from .rotations import spin1_rotation

    unitary = spin1_rotation(axis, angle_rad)
    return unitary @ rho @ unitary.conj().T


def populations_for_axis(p_tensor: float, p_vector: float = 0.0) -> np.ndarray:
    return np.array(
        [
            (2.0 + p_tensor + 3.0 * p_vector) / 6.0,
            (1.0 - p_tensor) / 3.0,
            (2.0 + p_tensor - 3.0 * p_vector) / 6.0,
        ]
    )


@dataclass(frozen=True)
class DensityDiagnostics:
    trace: complex
    purity: float
    eigenvalues: np.ndarray
    hermitian: bool


def diagnose(rho: np.ndarray) -> DensityDiagnostics:
    return DensityDiagnostics(
        trace=np.trace(rho),
        purity=float(np.trace(rho @ rho).real),
        eigenvalues=np.linalg.eigvalsh(rho),
        hermitian=bool(np.allclose(rho, rho.conj().T, atol=1.0e-12)),
    )
