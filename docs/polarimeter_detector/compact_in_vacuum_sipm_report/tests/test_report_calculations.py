from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np


REPORT_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = REPORT_DIR.parents[2]
sys.path.insert(0, str(REPORT_DIR / "scripts"))
sys.path.insert(0, str(REPOSITORY_ROOT / "code" / "data" / "energy_lise"))

from generate_report_data import chamber_metrics, sipm_response, ten_percent_energy_mev
from lise_range import available_model_keys, energy_loss_mev, load_range_table, particle_range_um


class SipmCalculationTest(unittest.TestCase):
    def test_eqr15_normal_upper_event(self) -> None:
        result = sipm_response(
            energy_mev=39.1,
            light_yield_photons_per_mev=10000.0,
            optical_efficiency=0.05,
            pde_fraction=0.45,
            microcells=167537,
            gain=4.0e5,
        )
        self.assertAlmostEqual(result.seed_photoelectrons, 8797.5, places=10)
        self.assertAlmostEqual(result.fired_cells, 8570.508658208, places=6)
        self.assertAlmostEqual(result.nonlinearity_percent, 2.5801800715, places=8)
        self.assertAlmostEqual(result.charge_nc, 0.5492587485, places=8)

    def test_ten_percent_energy_inverts_occupancy_model(self) -> None:
        energy_mev = ten_percent_energy_mev(
            light_yield_photons_per_mev=10000.0,
            optical_efficiency=0.05,
            pde_fraction=0.45,
            microcells=167537,
        )
        occupancy = energy_mev * 10000.0 * 0.05 * 0.45 / 167537.0
        response_ratio = (1.0 - math.exp(-occupancy)) / occupancy
        self.assertAlmostEqual(response_ratio, 0.9, places=12)

    def test_zero_energy_has_zero_output(self) -> None:
        result = sipm_response(
            energy_mev=0.0,
            light_yield_photons_per_mev=10000.0,
            optical_efficiency=0.05,
            pde_fraction=0.45,
            microcells=167537,
            gain=4.0e5,
        )
        self.assertEqual(result.fired_cells, 0.0)
        self.assertEqual(result.nonlinearity_percent, 0.0)
        self.assertEqual(result.charge_nc, 0.0)


class ChamberScreeningTest(unittest.TestCase):
    def test_current_aftersrc_closed_square_shell_mass(self) -> None:
        metrics = chamber_metrics(
            inner_x_mm=440.0,
            inner_y_mm=440.0,
            body_length_mm=420.0,
            wall_thickness_mm=8.0,
            density_g_per_cm3=7.90,
        )
        self.assertAlmostEqual(metrics.material_volume_l, 9.11872, places=6)
        self.assertAlmostEqual(metrics.mass_kg, 72.037888, places=6)
        self.assertEqual(metrics.outer_size_x_mm, 456.0)
        self.assertEqual(metrics.outer_size_y_mm, 456.0)


class LiseRangeTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table_path = (
            REPOSITORY_ROOT
            / "code"
            / "data"
            / "energy_lise"
            / "2H_C8H8_range_MeV_um.txt"
        )

    def test_primary_model_is_available(self) -> None:
        self.assertIn("atima_1_2_ls", available_model_keys())

    def test_zero_thickness_deposits_no_energy(self) -> None:
        table = load_range_table(self.table_path, "atima_1_2_ls")
        deposited = energy_loss_mev(2, np.array([2.0, 10.0, 19.5]), 0.0, table)
        np.testing.assert_allclose(deposited, np.zeros(3), atol=1.0e-12)

    def test_thick_detector_stops_deuteron(self) -> None:
        table = load_range_table(self.table_path, "atima_1_2_ls")
        deposited = energy_loss_mev(2, np.array([19.5]), 10_000.0, table)
        self.assertAlmostEqual(float(deposited[0]), 39.0, places=10)

    def test_range_interpolation_matches_tabulated_point(self) -> None:
        table = load_range_table(self.table_path, "atima_1_2_ls")
        tabulated_index = int(np.where(np.isclose(table.energy_mev_per_u, 10.0))[0][0])
        interpolated = particle_range_um(10.0, table)
        self.assertAlmostEqual(float(interpolated), float(table.range_um[tabulated_index]), places=12)


if __name__ == "__main__":
    unittest.main()
