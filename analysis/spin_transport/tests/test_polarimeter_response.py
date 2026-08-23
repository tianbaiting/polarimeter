from __future__ import annotations

from pathlib import Path

import numpy as np

from analysis.spin_transport.polarimeter_response import (
    DetectorGeometry,
    PolarimeterChannel,
    analyzing_powers_from_table,
    cross_section_factor,
    fit_axial_multi_channel,
    four_sector_yields,
    multi_channel_yields,
    proton_cm_from_lab,
    proton_cm_slope,
    sector_observables,
)
from analysis.spin_transport.spin1_density import axial_tensor


TABLE = Path("code/data/observables/CompletSetOFT/T.txt")


def test_cartesian_conversion_reproduces_repository_pyy_formula() -> None:
    analyzing = analyzing_powers_from_table(68.6, TABLE)
    pyy = 0.8
    tensor = axial_tensor(pyy, np.array([0.0, 1.0, 0.0]))
    left = cross_section_factor(tensor, 0.0, analyzing)
    up = cross_section_factor(tensor, 0.5 * np.pi, analyzing)
    expected_left = 1.0 - 0.5 * np.sqrt(3.0) * (-0.335) * pyy - 0.25 * np.sqrt(2.0) * 0.151 * pyy
    expected_up = 1.0 + 0.5 * np.sqrt(3.0) * (-0.335) * pyy - 0.25 * np.sqrt(2.0) * 0.151 * pyy
    assert np.isclose(left, expected_left)
    assert np.isclose(up, expected_up)


def test_rotated_pzz_generates_left_right_odd_harmonic() -> None:
    analyzing = analyzing_powers_from_table(68.6, TABLE)
    delta = np.radians(5.0)
    axis = np.array([np.sin(delta), 0.0, np.cos(delta)])
    yields = four_sector_yields(axial_tensor(0.8, axis), analyzing)
    observables = sector_observables(yields)
    assert yields["L"] != yields["R"]
    assert abs(observables["L-R"]) > 0.0


def test_vertical_mode_is_sector_symmetric_left_right_and_up_down() -> None:
    analyzing = analyzing_powers_from_table(68.6, TABLE)
    yields = four_sector_yields(axial_tensor(0.8, np.array([0.0, 1.0, 0.0])), analyzing)
    assert np.isclose(yields["L"], yields["R"])
    assert np.isclose(yields["U"], yields["D"])


def test_repository_proton_lab_angles_map_to_expected_cm_angles() -> None:
    assert np.isclose(np.degrees(proton_cm_from_lab(np.radians(53.4))), 68.67574005, atol=1.0e-7)
    assert np.isclose(np.degrees(proton_cm_from_lab(np.radians(11.2))), 155.70332401, atol=1.0e-7)


def test_centered_two_channel_fit_recovers_tensor_magnitude_and_axis() -> None:
    channels = []
    for name, theta_lab, radius in (("forward", 53.4, 205.0), ("backward", 11.2, 190.0)):
        theta_lab_rad = np.radians(theta_lab)
        theta_cm = np.degrees(proton_cm_from_lab(theta_lab_rad))
        channels.append(
            PolarimeterChannel(
                name,
                analyzing_powers_from_table(theta_cm, TABLE),
                DetectorGeometry(theta_lab, radius),
                1.0,
                theta_cm,
                proton_cm_slope(theta_lab_rad),
                TABLE,
                Path("code/data/observables/DSigamaOverDOmega.txt"),
            )
        )
    delta_deg = -5.1587
    axis = np.array([np.sin(np.radians(delta_deg)), 0.0, np.cos(np.radians(delta_deg))])
    observed = multi_channel_yields(axial_tensor(0.8, axis), channels)
    fitted = fit_axial_multi_channel(observed, channels, np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0]), (0.5, 1.0), (-12.0, 2.0))
    assert np.isclose(fitted["p_tensor"], 0.8, atol=2.0e-5)
    assert np.isclose(fitted["delta_deg"], delta_deg, atol=2.0e-4)
