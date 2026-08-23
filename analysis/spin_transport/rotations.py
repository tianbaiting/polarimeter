"""SO(3) and spin-1 rotation utilities."""

from __future__ import annotations

import numpy as np


def normalized(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(value)
    if norm == 0.0:
        raise ValueError("Rotation axis must be nonzero")
    return value / norm


def rotation_matrix(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    axis = normalized(axis)
    x, y, z = axis
    cross = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    identity = np.eye(3)
    # [EN] Rodrigues' form keeps chained beam-frame rotations orthogonal to numerical precision / [CN] Rodrigues 形式使链式束流坐标旋转在数值精度内保持正交
    return identity * np.cos(angle_rad) + (1.0 - np.cos(angle_rad)) * np.outer(axis, axis) + np.sin(angle_rad) * cross


def spin1_rotation(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    from .spin1_density import spin_matrices

    if angle_rad == 0.0:
        return np.eye(3, dtype=complex)
    axis = normalized(axis)
    sx, sy, sz = spin_matrices()
    generator = axis[0] * sx + axis[1] * sy + axis[2] * sz
    eigenvalues, eigenvectors = np.linalg.eigh(generator)
    phases = np.exp(-1.0j * angle_rad * eigenvalues)
    return (eigenvectors * phases) @ eigenvectors.conj().T


def rotate_tensor(tensor: np.ndarray, rotation: np.ndarray) -> np.ndarray:
    return rotation @ np.asarray(tensor, dtype=float) @ rotation.T


def compose(rotations: list[np.ndarray]) -> np.ndarray:
    total = np.eye(3)
    for rotation in rotations:
        total = rotation @ total
    return total
