#!/usr/bin/env python3
"""[EN] Compare true constant-density surfaces. / [CN] 比较真实的等概率密度面。"""

import argparse
from pathlib import Path

from plot_rnp_density import RadialModel
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np


def isosurface(model, pyy, level, ntheta=101, nphi=161):
    if not np.isfinite(level) or not 0 < level < model.density(0, 0, pyy):
        raise ValueError("The level must be positive and below the central density")
    if ntheta < 3 or nphi < 4:
        raise ValueError("The surface needs at least 3 polar and 4 azimuthal samples")
    theta = np.linspace(0, np.pi, ntheta)
    mu = np.cos(theta)
    radii = np.linspace(0, 16 * model.b, 4097)
    inside = model.density(radii[:, None], mu, pyy) >= level
    crossings = np.count_nonzero(inside[1:] != inside[:-1], axis=0)
    # [EN] A radial mesh represents one closed shell only; reject multiple shells. / [CN] 径向网格只表示一个闭合壳面，拒绝多壳面情形。
    if np.any(crossings != 1) or np.any(inside[-1]):
        raise ValueError("The selected level does not give one closed radial surface")
    indices = np.argmax(~inside, axis=0)
    low, high = radii[indices - 1], radii[indices]
    # [EN] Solve rho(r,theta)=level rather than scaling an ellipsoid by the density. / [CN] 求解 rho(r,theta)=level，而非按密度缩放椭球。
    for _ in range(50):
        middle = (low + high) / 2
        above = model.density(middle, mu, pyy) >= level
        low = np.where(above, middle, low)
        high = np.where(above, high, middle)
    radius = ((low + high) / 2)[:, None]
    phi = np.linspace(0, 2 * np.pi, nphi)[None, :]
    transverse = radius * np.sin(theta[:, None])
    x = transverse * np.cos(phi)
    y = np.broadcast_to(radius * mu[:, None], x.shape)
    z = transverse * np.sin(phi)
    return np.stack((x, y, z), axis=-1)


def surface_faces(surface):
    # [EN] Put physical y on the vertical display axis, preserving x,z horizontally. / [CN] 将物理 y 轴置于显示竖轴，x、z 轴置于水平面。
    displayed = surface[..., [0, 2, 1]]
    return np.stack((displayed[:-1, :-1], displayed[1:, :-1],
                     displayed[1:, 1:], displayed[:-1, 1:]), axis=-2).reshape(-1, 4, 3)


def shaded_colors(faces, color, alpha):
    normal = np.cross(faces[:, 2] - faces[:, 0], faces[:, 3] - faces[:, 1])
    norm = np.linalg.norm(normal, axis=1, keepdims=True)
    normal = np.divide(normal, norm, out=np.zeros_like(normal), where=norm > 0)
    centers = faces.mean(axis=1)
    normal *= np.where(np.sum(normal * centers, axis=1) < 0, -1, 1)[:, None]
    light = np.array([-0.5, -0.6, 1.0])
    light /= np.linalg.norm(light)
    brightness = 0.55 + 0.45 * np.clip(normal @ light, 0, 1)
    rgb = np.asarray(to_rgb(color))[None, :] * brightness[:, None]
    return np.column_stack((rgb, np.full(len(faces), alpha)))


def plot_isosurfaces(model, output_dir, level):
    plt.rcParams.update({"font.size": 11, "pdf.fonttype": 42})
    surfaces = [isosurface(model, pyy, level) for pyy in (1, -2)]
    meshes = [surface_faces(surface) for surface in surfaces]
    colors = ("#258BCB", "#ED8635")
    limit = 1.12 * max(np.abs(surface).max() for surface in surfaces)
    fig = plt.figure(figsize=(14, 5.2))
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.11, top=0.80, wspace=0.01)
    titles = (r"(a) $p_{yy}=+1$", r"(b) $p_{yy}=-2$", "(c) Transparent overlay")
    for panel, selected in enumerate(((0,), (1,), (0, 1))):
        ax = fig.add_subplot(1, 3, panel + 1, projection="3d")
        alpha = 0.24 if panel == 2 else 1.0
        faces = np.concatenate([meshes[index] for index in selected])
        facecolors = np.concatenate([shaded_colors(meshes[index], colors[index], alpha)
                                     for index in selected])
        # [EN] Sort both shells' faces together for intersecting transparent surfaces. / [CN] 将两壳面的面片统一深度排序，以绘制相交的透明表面。
        collection = Poly3DCollection(faces, facecolors=facecolors, edgecolors="none",
                                      linewidths=0, antialiased=True, zsort="average",
                                      rasterized=True)
        ax.add_collection3d(collection)
        ax.set(xlim=(-limit, limit), ylim=(-limit, limit), zlim=(-limit, limit),
               xlabel=r"$x_{np}$ [fm]", ylabel=r"$z_{np}$ [fm]",
               zlabel=r"$y_{np}$ [fm]", title=titles[panel])
        ax.set_box_aspect((1, 1, 1))
        ax.set_proj_type("ortho")
        ax.view_init(elev=18, azim=-55)
        ticks = [-round(limit * 0.75, 1), 0, round(limit * 0.75, 1)]
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis.set_ticks(ticks)
            axis.set_tick_params(labelsize=8, pad=0)
            axis.set_pane_color((0.96, 0.97, 0.98, 0.25))
            axis._axinfo["grid"].update(color=(0.6, 0.65, 0.7, 0.18), linewidth=0.5)
        ax.set_title(titles[panel], pad=7, fontsize=13)
    fig.suptitle(r"Neutron-proton constant-density surfaces: "
                 rf"$\varrho={level:g}\ \mathrm{{fm}}^{{-3}}$", y=0.97, fontsize=16)
    fig.text(0.5, 0.875, rf"Illustrative Gaussian S-D model: $b={model.b:g}$ fm, "
             rf"$P_D={100 * model.pd:g}\%$  |  Vertical axis: $y$  |  Same spatial scale",
             ha="center", fontsize=11)
    fig.legend(handles=[Patch(facecolor=color, label=label) for color, label in zip(
        colors, (r"$p_{yy}=+1$", r"$p_{yy}=-2$"))], loc="lower center",
        ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.005))
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png"):
        output = output_dir / f"rnp_isosurfaces_pyy.{extension}"
        fig.savefig(output, dpi=260)
        print(f"Saved {output}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b", type=float, default=2.0, help="Gaussian length in fm")
    parser.add_argument("--pd", type=float, default=0.05, help="D-state probability")
    parser.add_argument("--level", type=float, default=0.003, help="Absolute density in fm^-3")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parent / "output")
    args = parser.parse_args()
    try:
        plot_isosurfaces(RadialModel(args.b, args.pd), args.output_dir, args.level)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
