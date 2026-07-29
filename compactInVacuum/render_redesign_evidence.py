from __future__ import annotations

import argparse
from pathlib import Path
import re

import FreeCAD as App


VISIBLE_PHYSICAL = {
    "physical",
    "purchased_component_interface",
}
VISIBLE_DIAGNOSTIC = {
    *VISIBLE_PHYSICAL,
    "keepout",
    "physics_acceptance",
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    module_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prototype-dir",
        type=Path,
        default=module_root / "artifacts" / "redesign_v2" / "after" / "prototypes",
    )
    parser.add_argument(
        "--after-src",
        type=Path,
        default=module_root
        / "artifacts"
        / "afterSRC"
        / "CompactOne_afterSRC.FCStd",
    )
    parser.add_argument(
        "--pre-samurai",
        type=Path,
        default=module_root
        / "artifacts"
        / "infrontSamurai"
        / "CompactOne_infrontSamurai.FCStd",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=module_root / "artifacts" / "redesign_v2" / "after" / "screenshots",
    )
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=900)
    return parser.parse_known_args(argv)[0]


def _start_gui():
    if not App.listDocuments():
        App.newDocument("__CIVRenderBootstrap")
    import FreeCADGui as Gui

    Gui.showMainWindow()
    return Gui


def _set_roles(document, visible_roles: set[str]) -> None:
    for obj in document.Objects:
        if not hasattr(obj, "ViewObject") or not hasattr(obj, "EngineeringRole"):
            continue
        role = str(obj.EngineeringRole)
        visible = role in visible_roles
        if role == "keepout" and obj.Name.endswith(
            (
                "DetectorRemovalEnvelope",
                "SectorRemovalEnvelope",
                "TargetCompleteMotionSweep",
            )
        ):
            visible = False
        obj.ViewObject.Visibility = visible
        if visible and role == "keepout":
            obj.ViewObject.Transparency = 88
        elif visible and role == "physics_acceptance":
            obj.ViewObject.Transparency = 78


def _render(
    gui,
    source: Path,
    destination: Path,
    visible_roles: set[str],
    view_name: str,
    width: int,
    height: int,
) -> None:
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    # [EN] Fix the GUI viewport size so saved-image framing does not depend on machine-local FreeCAD window state. / [CN] 固定 GUI 视口尺寸，避免保存图像的构图依赖本机 FreeCAD 窗口状态。
    gui.getMainWindow().resize(width, height)
    gui.updateGui()
    document = App.openDocument(str(source))
    gui.setActiveDocument(document.Name)
    _set_roles(document, visible_roles)
    if "transparent" in destination.name.lower():
        for name in ("LightTightSleeve", "ReflectorEnvelope"):
            housing_layer = document.getObject(name)
            if housing_layer is not None:
                housing_layer.ViewObject.Visibility = False
    # [EN] Flush visibility changes before fitAll so hidden removal envelopes cannot dominate the camera scale. / [CN] 在 fitAll 前刷新可见性，避免已隐藏的拆卸包络支配相机缩放。
    gui.updateGui()
    view = gui.getDocument(document.Name).activeView()
    view.setAnimationEnabled(False)
    if view_name == "right":
        view.viewRight()
    elif view_name == "front":
        view.viewFront()
    elif view_name == "top":
        view.viewTop()
    else:
        view.viewAxonometric()
    view.fitAll()
    camera_text = view.getCamera()
    height_match = re.search(r"(?m)^  height ([0-9.eE+-]+)$", camera_text)
    if height_match is not None:
        fitted_height = float(height_match.group(1))
        zoom_factor = (
            1.08
            if "sector_holder" in destination.name
            else (0.95 if "detector_head" in destination.name else 1.15)
        )
        camera_text = (
            camera_text[: height_match.start(1)]
            + f"{zoom_factor * fitted_height:.9g}"
            + camera_text[height_match.end(1) :]
        )
        view.setCamera(camera_text)
    gui.updateGui()
    destination.parent.mkdir(parents=True, exist_ok=True)
    view.saveImage(str(destination.resolve()), width, height, "White")
    gui.updateGui()
    App.closeDocument(document.Name)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    prototype_dir = args.prototype_dir.resolve()
    gui = _start_gui()
    if "__CIVRenderBootstrap" in App.listDocuments():
        App.closeDocument("__CIVRenderBootstrap")

    jobs = (
        (
            prototype_dir / "CompactOne_detector_head.FCStd",
            args.output_dir / "detector_head_side.png",
            VISIBLE_PHYSICAL,
            "right",
        ),
        (
            prototype_dir / "CompactOne_detector_head_transparent.FCStd",
            args.output_dir / "detector_head_transparent_side.png",
            VISIBLE_PHYSICAL,
            "right",
        ),
        (
            prototype_dir / "CompactOne_sector_holder.FCStd",
            args.output_dir / "sector_holder_isometric.png",
            VISIBLE_PHYSICAL,
            "isometric",
        ),
        (
            prototype_dir / "CompactOne_sector_holder.FCStd",
            args.output_dir / "sector_holder_diagnostic.png",
            VISIBLE_DIAGNOSTIC,
            "isometric",
        ),
        (
            prototype_dir / "CompactOne_four_sector_internal.FCStd",
            args.output_dir / "four_sector_internal_isometric.png",
            VISIBLE_PHYSICAL,
            "isometric",
        ),
        (
            prototype_dir / "CompactOne_four_sector_internal.FCStd",
            args.output_dir / "four_sector_internal_diagnostic.png",
            VISIBLE_DIAGNOSTIC,
            "isometric",
        ),
        (
            args.after_src,
            args.output_dir / "CompactInVacuum_afterSRC_isometric.png",
            VISIBLE_PHYSICAL,
            "isometric",
        ),
        (
            args.pre_samurai,
            args.output_dir / "CompactInVacuum_preSAMURAI_isometric.png",
            VISIBLE_PHYSICAL,
            "isometric",
        ),
    )
    for source, destination, roles, view_name in jobs:
        _render(
            gui,
            source,
            destination,
            set(roles),
            view_name,
            args.width,
            args.height,
        )
        print(destination.resolve())
    # [EN] FCStd retains all engineering roles; these PNGs deliberately separate physical inspection from diagnostic overlays. / [CN] FCStd 保留全部工程角色；这些 PNG 有意将物理检查与诊断叠加层分开。
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
