#!/usr/bin/env python3
"""[EN] Plot a normalized illustrative S–D model. / [CN] 绘制归一化 S–D 示意模型。"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np


@dataclass(frozen=True)
class RadialModel:
    b: float = 2.0
    pd: float = 0.05

    def __post_init__(self):
        if not np.isfinite(self.b) or self.b <= 0:
            raise ValueError("b must be finite and positive")
        if not np.isfinite(self.pd) or not 0 <= self.pd <= 1:
            raise ValueError("D-state probability must be in [0, 1]")

    def reduced_over_r(self, r):
        # [EN] Analytic u/r and w/r avoid a singular division at the origin. / [CN] 解析计算 u/r 和 w/r，避免原点处的奇异除法。
        r = np.asarray(r, dtype=float)
        q = r / self.b
        common = np.exp(-0.5 * q**2) / (np.pi**0.25 * self.b**1.5)
        return (2 * np.sqrt(1 - self.pd) * common,
                4 * np.sqrt(self.pd / 15) * q**2 * common)

    def radial_functions(self, r):
        r = np.asarray(r, dtype=float)
        ur, wr = self.reduced_over_r(r)
        return r * ur, r * wr

    def radial_probability(self, r):
        u, w = self.radial_functions(r)
        return u**2 + w**2

    def density(self, r, mu, pyy):
        if not np.isfinite(pyy) or not -2 <= pyy <= 1:
            raise ValueError("pyy must be in [-2, 1]")
        ur, wr = self.reduced_over_r(r)
        # [EN] Retain coherent S–D interference in the spin-traced density. / [CN] 对自旋取迹后的密度保留相干 S–D 干涉。
        quadrupole = np.sqrt(2) * ur * wr - 0.5 * wr**2
        return (ur**2 + wr**2 + pyy * quadrupole * p2(mu)) / (4 * np.pi)

    def angular_probability(self, mu, pyy):
        # [EN] Integrating r and azimuth gives dP/dmu, not dP/dtheta. / [CN] 对半径和方位角积分得到 dP/dmu，而非 dP/dtheta。
        coefficient = np.sqrt(6 / 5 * self.pd * (1 - self.pd)) - self.pd / 2
        return 0.5 * (1 + pyy * coefficient * p2(mu))


def p2(mu):
    return 0.5 * (3 * np.asarray(mu)**2 - 1)


def plot_density(model, output_dir, extent, points):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42})
    coordinate = np.linspace(-extent, extent, points)
    x, y = np.meshgrid(coordinate, coordinate)
    r = np.hypot(x, y)
    mu = np.divide(y, r, out=np.zeros_like(r), where=r > 0)
    densities = [model.density(r, mu, pyy) for pyy in (1, -2)]
    # [EN] A common absolute scale permits direct comparison of both states. / [CN] 两态共用绝对色标以便直接比较。
    norm = Normalize(0, max(float(d.max()) for d in densities))
    fig = plt.figure(figsize=(10.4, 8.3), layout="constrained")
    grid = fig.add_gridspec(2, 3, width_ratios=(1, 1, 0.045),
                           height_ratios=(1.1, 0.8))
    for index, (density, label) in enumerate(zip(
            densities, (r"(a) $p_{yy}=+1$", r"(b) $p_{yy}=-2$"))):
        ax = fig.add_subplot(grid[0, index])
        mesh = ax.pcolormesh(x, y, density, cmap="magma", norm=norm,
                             shading="auto", rasterized=True)
        ax.contour(x, y, density, levels=norm.vmax * np.array([0.1, 0.3, 0.6]),
                   colors="white", linewidths=0.6, alpha=0.65)
        ax.set(xlabel=r"$x_{np}$ [fm]", ylabel=r"$y_{np}$ [fm] (vertical)",
               title=label, aspect="equal")
    bar = fig.colorbar(mesh, cax=fig.add_subplot(grid[0, 2]))
    bar.set_label(r"$\varrho(x_{np},y_{np},z_{np}=0)$ [fm$^{-3}$]")
    bar.formatter.set_powerlimits((0, 0))
    bar.update_ticks()

    radial_ax = fig.add_subplot(grid[1, 0])
    angular_ax = fig.add_subplot(grid[1, 1])
    radius = np.linspace(0, 1.5 * extent, 1001)
    cosine = np.linspace(-1, 1, 501)
    for pyy, color, style in ((1, "#0072B2", "-"), (-2, "#D55E00", "--")):
        label = rf"$p_{{yy}}={pyy:+d}$"
        radial_ax.plot(radius, model.radial_probability(radius), style,
                       color=color, lw=2.2, label=label)
        angular_ax.plot(cosine, model.angular_probability(cosine, pyy),
                        style, color=color, lw=2.2, label=label)
    radial_ax.set(xlabel=r"$r_{np}=|\mathbf{r}_p-\mathbf{r}_n|$ [fm]",
                  ylabel=r"$P(r_{np})$ [fm$^{-1}$]",
                  title="(c) Radial distance: identical distributions",
                  xlim=(0, radius[-1]), ylim=(0, None))
    angular_ax.axhline(0.5, color="0.45", lw=1, ls=":", label="Unpolarized")
    angular_ax.set(xlabel=r"$\mu=\cos\theta_y$",
                   ylabel=r"$dP/d\mu$", title="(d) Direction: different distributions",
                   xlim=(-1, 1), ylim=(0, 1))
    for ax in (radial_ax, angular_ax):
        ax.legend(frameon=False, fontsize=9)
        ax.grid(alpha=0.18)
    fig.suptitle("Neutron–proton relative-coordinate probability density\n"
                 rf"Illustrative Gaussian S–D model: $b={model.b:g}$ fm, "
                 rf"$P_D={100 * model.pd:g}\%$; spatial slices at $z_{{np}}=0$",
                 fontsize=13)
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png"):
        output = output_dir / f"rnp_density_pyy.{extension}"
        fig.savefig(output, dpi=220)
        print(f"Saved {output}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b", type=float, default=2.0, help="Gaussian length in fm")
    parser.add_argument("--pd", type=float, default=0.05, help="D-state probability")
    parser.add_argument("--extent", type=float, default=6.0, help="Slice half-width in fm")
    parser.add_argument("--points", type=int, default=501, help="Grid points per axis")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parent / "output")
    args = parser.parse_args()
    if not np.isfinite(args.extent) or args.extent <= 0 or args.points < 3:
        parser.error("extent must be finite and positive; points must be at least 3")
    try:
        model = RadialModel(args.b, args.pd)
    except ValueError as error:
        parser.error(str(error))
    plot_density(model, args.output_dir, args.extent, args.points)


if __name__ == "__main__":
    main()
