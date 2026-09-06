from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import trimesh


GROUP_STYLE = {
    "chamber": ("#9aa0a6", 0.12),
    "internals": ("#a9782d", 0.92),
    "services": ("#4f5966", 0.95),
    "support": ("#247ba0", 1.00),
    "access": ("#d1493f", 0.58),
}

VIEWS = {
    "isometric": (24.0, -42.0),
    "front": (0.0, -90.0),
    "top": (90.0, -90.0),
    "right": (0.0, 0.0),
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    module_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", type=Path)
    parser.add_argument("--title", default="CompactInVacuum")
    parser.add_argument("--basename", default="support_review")
    parser.add_argument("--internals-only", action="store_true")
    parser.add_argument(
        "--study-root",
        type=Path,
        default=module_root / "artifacts" / "access_port_study",
    )
    return parser.parse_args(argv)


def _load_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh):
        raise TypeError(f"unsupported mesh at {path}")
    return loaded


def _display_vertices(mesh: trimesh.Trimesh) -> np.ndarray:
    vertices = np.asarray(mesh.vertices)
    # [EN] Display Y as vertical and beam Z as drawing depth/horizontal so the configured +Y maintenance wall reads as the physical top. / [CN] 显示时以 Y 为竖直方向、束流 Z 为图纸深度/水平轴，使配置中的 +Y 检修壁对应物理顶面。
    return vertices[:, (0, 2, 1)]


def _render_model(model_root: Path, title: str, basename: str, internals_only: bool = False) -> None:
    mesh_dir = model_root / "review_meshes"
    screenshot_dir = model_root / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    meshes = {
        name: _load_mesh(mesh_dir / f"{name}.stl")
        for name in GROUP_STYLE
        if not internals_only or name in {"internals", "support"}
    }
    all_vertices = np.vstack([_display_vertices(mesh) for mesh in meshes.values()])
    mins = all_vertices.min(axis=0)
    maxs = all_vertices.max(axis=0)
    center = 0.5 * (mins + maxs)
    span = 0.55 * float(np.max(maxs - mins))
    for view_name, (elevation, azimuth) in VIEWS.items():
        figure = plt.figure(figsize=(14.0, 9.0), dpi=100)
        axis = figure.add_subplot(111, projection="3d")
        for group_name in (
            "internals",
            "support",
            "services",
            "access",
            "chamber",
        ):
            if group_name not in meshes:
                continue
            mesh = meshes[group_name]
            vertices = _display_vertices(mesh)
            color, alpha = GROUP_STYLE[group_name]
            axis.plot_trisurf(
                vertices[:, 0],
                vertices[:, 1],
                vertices[:, 2],
                triangles=np.asarray(mesh.faces),
                color=color,
                alpha=alpha,
                linewidth=0.04,
                edgecolor="#303030" if group_name == "access" else "none",
                shade=True,
            )
        axis.set_xlim(center[0] - span, center[0] + span)
        axis.set_ylim(center[1] - span, center[1] + span)
        axis.set_zlim(center[2] - span, center[2] + span)
        axis.set_box_aspect((1.0, 1.0, 1.0))
        axis.view_init(elev=elevation, azim=azimuth)
        axis.set_axis_off()
        axis.set_title(
            f"{title} — {view_name}",
            fontsize=14,
        )
        figure.patch.set_facecolor("white")
        destination = screenshot_dir / (
            f"{basename}_{view_name}.png"
        )
        figure.savefig(destination, bbox_inches="tight", facecolor="white")
        plt.close(figure)
        print(destination)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    study_root = args.study_root.resolve()
    if args.model_root:
        _render_model(args.model_root.resolve(), args.title, args.basename, args.internals_only)
        return 0
    for standard in ("ICF253", "ICF305", "ICF356"):
        _render_model(study_root / standard.lower(), f"CompactInVacuum-afterSRC {standard} maintenance access", f"CompactOne_afterSRC_access_{standard}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
