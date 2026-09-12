"""[EN] Check normalization and polarization limits. / [CN] 检查归一化及极化极限。"""

import unittest

import numpy as np

from plot_rnp_density import RadialModel
from plot_rnp_isosurfaces import isosurface


class DensityTests(unittest.TestCase):
    def setUp(self):
        self.model = RadialModel()
        self.r = np.linspace(0, 24, 12001)
        self.mu, self.weights = np.polynomial.legendre.leggauss(12)

    def test_radial_normalization_and_d_probability(self):
        u, w = self.model.radial_functions(self.r)
        self.assertAlmostEqual(np.trapezoid(u**2 + w**2, self.r), 1, places=12)
        self.assertAlmostEqual(np.trapezoid(w**2, self.r), self.model.pd, places=12)

    def test_angular_integration_recovers_same_radial_density(self):
        for pyy in (-2, 0, 1):
            density = self.model.density(self.r[:, None], self.mu, pyy)
            radial = 2 * np.pi * self.r**2 * (density @ self.weights)
            np.testing.assert_allclose(radial, self.model.radial_probability(self.r),
                                       rtol=2e-14, atol=1e-16)

    def test_angular_marginal_matches_volume_integral(self):
        for pyy in (-2, 1):
            density = self.model.density(self.r[:, None], self.mu, pyy)
            marginal = 2 * np.pi * np.trapezoid(self.r[:, None]**2 * density,
                                               self.r, axis=0)
            np.testing.assert_allclose(marginal,
                                       self.model.angular_probability(self.mu, pyy),
                                       atol=1e-13, rtol=0)
            self.assertAlmostEqual(marginal @ self.weights, 1, places=12)

    def test_positive_density_and_regular_origin(self):
        for pd in (0, 0.05, 0.5, 1):
            model = RadialModel(pd=pd)
            for pyy in (-2, 0, 1):
                density = model.density(self.r[:, None], np.linspace(-1, 1, 51), pyy)
                self.assertTrue(np.all(np.isfinite(density)))
                self.assertGreaterEqual(float(density.min()), -1e-17)
                np.testing.assert_allclose(density[0], density[0, 0], atol=1e-16)

    def test_s_wave_isotropic_and_enhancement_directions(self):
        s_only = RadialModel(pd=0)
        np.testing.assert_allclose(s_only.density(self.r, 1, 1),
                                   s_only.density(self.r, 0, -2), atol=1e-16)
        self.assertGreater(self.model.density(2, 1, 1), self.model.density(2, 0, 1))
        self.assertLess(self.model.density(2, 1, -2), self.model.density(2, 0, -2))

    def test_invalid_parameters(self):
        for parameters in ({"b": 0}, {"b": float("nan")}, {"pd": -0.1}, {"pd": 1.1}):
            with self.assertRaises(ValueError):
                RadialModel(**parameters)


class IsosurfaceTests(unittest.TestCase):
    def test_z_axis_surface_density_and_rotation(self):
        model = RadialModel()
        y_surface = isosurface(model, 1, 0.003, ntheta=31, nphi=41)
        z_surface = isosurface(model, 1, 0.003, ntheta=31, nphi=41, axis="z")
        r = np.linalg.norm(z_surface, axis=-1)
        np.testing.assert_allclose(model.density(r, z_surface[..., 2] / r, 1),
                                   0.003, atol=1e-16, rtol=0)
        np.testing.assert_allclose(r, np.linalg.norm(y_surface, axis=-1), atol=1e-14)
        np.testing.assert_allclose(z_surface[..., 0], y_surface[..., 0], atol=1e-14)
        np.testing.assert_allclose(z_surface[..., 1], -y_surface[..., 2], atol=1e-14)
        np.testing.assert_allclose(z_surface[..., 2], y_surface[..., 1], atol=1e-14)
        self.assertGreater(np.max(z_surface[..., 2]), np.max(z_surface[..., 1]))
        self.assertGreater(np.max(z_surface[..., 2]), np.max(z_surface[..., 0]))

    def test_invalid_symmetry_axis_is_rejected(self):
        with self.assertRaises(ValueError):
            isosurface(RadialModel(), 1, 0.003, axis="invalid")

    def test_surface_satisfies_absolute_density_and_closes(self):
        model = RadialModel()
        for pyy in (1, -2):
            surface = isosurface(model, pyy, 0.003, ntheta=31, nphi=41)
            r = np.linalg.norm(surface, axis=-1)
            np.testing.assert_allclose(model.density(r, surface[..., 1] / r, pyy),
                                       0.003, atol=1e-16, rtol=0)
            np.testing.assert_allclose(surface[:, 0], surface[:, -1], atol=1e-14)
            np.testing.assert_allclose(surface[0], np.broadcast_to(surface[0, 0],
                                                                  surface[0].shape), atol=1e-14)
            equatorial_radius, axial_radius = r[15, 0], r[0, 0]
            self.assertGreater(pyy * (axial_radius - equatorial_radius), 0)

    def test_s_wave_surface_matches_analytic_sphere(self):
        model = RadialModel(pd=0)
        level = 0.003
        expected = model.b * np.sqrt(np.log(model.density(0, 0, 0) / level))
        surface = isosurface(model, 1, level, ntheta=21, nphi=31)
        np.testing.assert_allclose(np.linalg.norm(surface, axis=-1), expected,
                                   atol=1e-14, rtol=0)

    def test_invalid_levels_are_rejected(self):
        model = RadialModel()
        for level in (0, -1, np.nan, model.density(0, 0, 1), 1):
            with self.assertRaises(ValueError):
                isosurface(model, 1, level)


if __name__ == "__main__":
    unittest.main()
