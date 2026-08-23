from __future__ import annotations

import numpy as np

from analysis.spin_transport.beamline import AXES, BeamlineElement, transport_density
from analysis.spin_transport.bmt import DEUTERON_ANOMALY, gamma_from_kinetic_energy, ideal_dipole_spin_angles
from analysis.spin_transport.ensemble import gaussian_phase_average
from analysis.spin_transport.rotations import rotation_matrix
from analysis.spin_transport.spin1_density import (
    axial_density_matrix,
    axial_tensor,
    density_from_components,
    diagnose,
    rotate_density,
    tensor_components,
)


def test_density_matrix_physical_invariants() -> None:
    rho = axial_density_matrix(0.8, np.array([0.0, 0.0, 1.0]))
    diagnostics = diagnose(rho)
    assert diagnostics.hermitian
    assert np.isclose(diagnostics.trace, 1.0)
    assert np.min(diagnostics.eigenvalues) >= -1.0e-13
    assert np.allclose(diagnostics.eigenvalues, [1.0 / 15.0, 7.0 / 15.0, 7.0 / 15.0])


def test_repository_population_normalization() -> None:
    for p_tensor in (-2.0, -0.7, 0.0, 0.8, 1.0):
        rho = axial_density_matrix(p_tensor, np.array([0.0, 0.0, 1.0]))
        populations = np.real(np.diag(rho))
        recovered = populations[0] + populations[2] - 2.0 * populations[1]
        assert np.isclose(recovered, p_tensor)


def test_coherent_rotation_preserves_trace_eigenvalues_and_purity() -> None:
    rho = axial_density_matrix(0.8, np.array([0.0, 0.0, 1.0]))
    rotated = rotate_density(rho, np.array([0.0, 1.0, 0.0]), 0.37)
    before, after = diagnose(rho), diagnose(rotated)
    assert np.isclose(after.trace, 1.0)
    assert np.isclose(after.purity, before.purity)
    assert np.allclose(after.eigenvalues, before.eigenvalues)


def test_spin1_unitary_and_cartesian_rotation_agree() -> None:
    tensor = np.array([[0.1, 0.08, -0.03], [0.08, -0.4, 0.07], [-0.03, 0.07, 0.3]])
    rho = density_from_components(tensor=tensor)
    axis = np.array([0.3, -0.4, 0.5])
    angle = 0.41
    rotated_rho = rotate_density(rho, axis, angle)
    rotation = rotation_matrix(axis, angle)
    assert np.allclose(tensor_components(rotated_rho), rotation @ tensor @ rotation.T, atol=1.0e-12)


def test_ideal_horizontal_bend_preserves_vertical_tensor_mode() -> None:
    p_tensor = 0.8
    tensor = axial_tensor(p_tensor, np.array([0.0, 1.0, 0.0]))
    rotation = rotation_matrix(np.array([0.0, 1.0, 0.0]), 0.23)
    assert np.allclose(rotation @ tensor @ rotation.T, tensor, atol=1.0e-13)


def test_longitudinal_analytic_tensor_components_and_sign() -> None:
    p_tensor = 0.8
    delta = 0.19
    rho = axial_density_matrix(p_tensor, np.array([0.0, 0.0, 1.0]))
    tensor = tensor_components(rotate_density(rho, np.array([0.0, 1.0, 0.0]), delta))
    assert np.isclose(tensor[0, 0], p_tensor * (np.sin(delta) ** 2 - 0.5 * np.cos(delta) ** 2))
    assert np.isclose(tensor[1, 1], -0.5 * p_tensor)
    assert np.isclose(tensor[2, 2], p_tensor * (np.cos(delta) ** 2 - 0.5 * np.sin(delta) ** 2))
    assert np.isclose(tensor[0, 2], 1.5 * p_tensor * np.sin(delta) * np.cos(delta))


def test_zero_bend_is_exact_identity() -> None:
    rho = axial_density_matrix(0.8, np.array([0.0, 0.0, 1.0]))
    assert np.array_equal(rotate_density(rho, np.array([0.0, 1.0, 0.0]), 0.0), rho)


def test_deuteron_bmt_numerics_at_380_mev() -> None:
    gamma = gamma_from_kinetic_energy(380.0)
    _, relative = ideal_dipole_spin_angles(np.radians(30.0), gamma)
    assert np.isclose(gamma, 1.20260044, atol=2.0e-8)
    assert np.isclose(DEUTERON_ANOMALY, -0.14298727, atol=2.0e-8)
    assert np.isclose(DEUTERON_ANOMALY * gamma, -0.17195655, atol=2.0e-8)
    assert np.isclose(np.degrees(relative), -5.15870, atol=1.0e-4)


def test_beamline_local_frame_matches_relative_rotation() -> None:
    rho = axial_density_matrix(0.8, AXES["z"])
    element = BeamlineElement("illustrative", "dipole", AXES["y"], np.radians(10.0), 380.0)
    state = transport_density(rho, [element])
    expected_delta = DEUTERON_ANOMALY * gamma_from_kinetic_energy(380.0) * np.radians(10.0)
    assert np.allclose(tensor_components(state.rho_beam), axial_tensor(0.8, rotation_matrix(AXES["y"], expected_delta) @ AXES["z"]), atol=1.0e-12)


def test_gaussian_phase_spread_reduces_purity_but_preserves_trace() -> None:
    rho = axial_density_matrix(0.8, AXES["z"])
    averaged = gaussian_phase_average(rho, AXES["y"], 0.1, np.radians(8.0))
    assert np.isclose(np.trace(averaged), 1.0)
    assert diagnose(averaged).purity < diagnose(rho).purity
