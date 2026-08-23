"""Ordered orbit-frame and spin-frame transport through a configurable lattice."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import numpy as np

from .bmt import DEUTERON_ANOMALY, gamma_from_kinetic_energy, ideal_dipole_spin_angles
from .rotations import rotation_matrix, spin1_rotation


AXES = {"x": np.array([1.0, 0.0, 0.0]), "y": np.array([0.0, 1.0, 0.0]), "z": np.array([0.0, 0.0, 1.0])}


@dataclass(frozen=True)
class BeamlineElement:
    name: str
    element_type: str
    bend_axis: np.ndarray
    orbit_bend_rad: float
    kinetic_energy_mev: float
    spin_rotation_rad: float | None = None
    source: str = "illustrative"

    @property
    def gamma(self) -> float:
        return gamma_from_kinetic_energy(self.kinetic_energy_mev)

    @property
    def resolved_spin_rotation_rad(self) -> float:
        if self.spin_rotation_rad is not None:
            return self.spin_rotation_rad
        return ideal_dipole_spin_angles(self.orbit_bend_rad, self.gamma)[0]


@dataclass
class TransportState:
    rho_lab: np.ndarray
    orbit_frame: np.ndarray = field(default_factory=lambda: np.eye(3))
    spin_rotation: np.ndarray = field(default_factory=lambda: np.eye(3))
    history: list[dict[str, float | str]] = field(default_factory=list)

    @property
    def rho_beam(self) -> np.ndarray:
        # [EN] The local beam basis is removed from the lab spin state before polarimeter observables are formed / [CN] 在构造极化仪可观测量前，从实验室自旋态中去除局域束流基底旋转
        return self._rho_in_local_frame()

    def _rho_in_local_frame(self) -> np.ndarray:
        axis, angle = axis_angle(self.orbit_frame.T)
        unitary = spin1_rotation(axis, angle)
        return unitary @ self.rho_lab @ unitary.conj().T


def axis_angle(rotation: np.ndarray) -> tuple[np.ndarray, float]:
    cosine = np.clip((np.trace(rotation) - 1.0) / 2.0, -1.0, 1.0)
    angle = float(np.arccos(cosine))
    if abs(angle) < 1.0e-14:
        return AXES["z"], 0.0
    vector = np.array([rotation[2, 1] - rotation[1, 2], rotation[0, 2] - rotation[2, 0], rotation[1, 0] - rotation[0, 1]])
    if np.linalg.norm(vector) < 1.0e-10:
        values, vectors = np.linalg.eigh(rotation)
        axis = vectors[:, np.argmin(np.abs(values - 1.0))].real
    else:
        axis = vector / (2.0 * np.sin(angle))
    return axis / np.linalg.norm(axis), angle


def transport_density(rho_initial: np.ndarray, elements: list[BeamlineElement]) -> TransportState:
    rho_lab = np.asarray(rho_initial, dtype=complex).copy()
    orbit_frame = np.eye(3)
    spin_total = np.eye(3)
    history: list[dict[str, float | str]] = []
    for element in elements:
        orbit_rotation = rotation_matrix(element.bend_axis, element.orbit_bend_rad)
        spin_rotation = rotation_matrix(element.bend_axis, element.resolved_spin_rotation_rad)
        spin_unitary = spin1_rotation(element.bend_axis, element.resolved_spin_rotation_rad)
        rho_lab = spin_unitary @ rho_lab @ spin_unitary.conj().T
        orbit_frame = orbit_rotation @ orbit_frame
        spin_total = spin_rotation @ spin_total
        history.append(
            {
                "name": element.name,
                "orbit_bend_deg": float(np.degrees(element.orbit_bend_rad)),
                "spin_lab_deg": float(np.degrees(element.resolved_spin_rotation_rad)),
                "relative_increment_deg": float(np.degrees(element.resolved_spin_rotation_rad - element.orbit_bend_rad)),
            }
        )
    return TransportState(rho_lab=rho_lab, orbit_frame=orbit_frame, spin_rotation=spin_total, history=history)


def element_from_mapping(data: dict[str, Any]) -> BeamlineElement:
    axis_data = data.get("bend_axis", "y")
    axis = AXES[axis_data] if isinstance(axis_data, str) else np.asarray(axis_data, dtype=float)
    return BeamlineElement(
        name=str(data["name"]),
        element_type=str(data.get("type", "dipole")),
        bend_axis=axis,
        orbit_bend_rad=np.radians(float(data.get("orbit_bend_deg", 0.0))),
        kinetic_energy_mev=float(data.get("kinetic_energy_mev", 380.0)),
        spin_rotation_rad=None if "spin_rotation_deg" not in data else np.radians(float(data["spin_rotation_deg"])),
        source=str(data.get("source", "illustrative")),
    )


def load_lattice(path: str | Path) -> list[BeamlineElement]:
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(content)
    else:
        try:
            import yaml
        except ImportError as error:
            raise RuntimeError("PyYAML is required to read YAML beamlines") from error
        data = yaml.safe_load(content)
    return [element_from_mapping(item) for item in data["elements"]]
