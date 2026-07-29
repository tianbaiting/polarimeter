from __future__ import annotations

import os

import FreeCAD as App


PHYSICAL = "physical"
PURCHASED = "purchased_component_interface"
KEEPOUT = "keepout"
DATUM = "datum"
SERVICE_CENTERLINE = "service_centerline"
PHYSICS_ACCEPTANCE = "physics_acceptance"
OPTIONAL_REFERENCE = "optional_reference_geometry"

VISIBLE_BY_DEFAULT = {PHYSICAL, PURCHASED}


def ensure_gui_session() -> None:
    if App.GuiUp:
        return
    if os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
        # [EN] FreeCAD 1.0 can deadlock while attaching its main window to the Qt offscreen plugin; geometry export remains available through the non-GUI path. / [CN] FreeCAD 1.0 在将主窗口附加到 Qt offscreen 插件时可能死锁；几何导出仍可通过非 GUI 路径完成。
        return
    try:
        import FreeCADGui as Gui

        if not App.listDocuments():
            App.newDocument("__CIVGuiBootstrap")
        # [EN] FreeCAD 0.20 needs an existing bootstrap document before headless GUI attachment; the assembly factory removes it after creating the real document. / [CN] FreeCAD 0.20 在无头 GUI 附加前需要已有的引导文档；装配工厂创建真实文档后会将其移除。
        Gui.showMainWindow()
    except Exception:
        # [EN] Geometry generation remains valid without GUI state; runtime geometry tests intentionally exercise this fallback. / [CN] 即使没有 GUI 状态，几何生成仍有效；运行时几何测试会有意覆盖此回退路径。
        return


def _shape_color(name: str, role: str) -> tuple[float, float, float]:
    if "ActivePlastic" in name:
        return (0.08, 0.72, 0.88)
    if "ReflectorEnvelope" in name:
        return (0.92, 0.92, 0.86)
    if "OpticalCoupling" in name:
        return (0.95, 0.65, 0.18)
    if "SiPMPackage" in name:
        return (0.12, 0.30, 0.62)
    if "SensorPCBCarrier" in name or "RearMountingFace" in name:
        return (0.80, 0.43, 0.16)
    if "LightTightSleeve" in name:
        return (0.10, 0.11, 0.13)
    if any(
        token in name
        for token in (
            "SectorCarrierPlate",
            "DetectorNestCradle",
            "RemovableClampBridge",
            "SectorInterfaceBlock",
        )
    ):
        return (0.78, 0.62, 0.28)
    if "Target" in name:
        return (0.82, 0.22, 0.42)
    if "Chamber" in name or "Transition" in name:
        return (0.66, 0.70, 0.74)
    if role == PURCHASED:
        return (0.34, 0.38, 0.44)
    if role == KEEPOUT:
        return (0.95, 0.35, 0.12)
    if role == PHYSICS_ACCEPTANCE:
        return (0.25, 0.90, 0.32)
    return (0.58, 0.62, 0.68)


def _transparency(name: str, role: str) -> int:
    if role in {KEEPOUT, PHYSICS_ACCEPTANCE, OPTIONAL_REFERENCE}:
        return 75
    if role == DATUM:
        return 40
    if "ProjectChamberBody" in name:
        return 78
    if "OpticalCoupling" in name:
        return 35
    return 0


def _document_group(doc: App.Document, group_name: str) -> App.DocumentObject:
    existing = doc.getObject(group_name)
    if existing is not None:
        return existing
    return doc.addObject("App::DocumentObjectGroup", group_name)


def add_feature(
    doc: App.Document,
    name: str,
    shape,
    role: str = PHYSICAL,
    group_name: str = "OptionalReference",
    material: str | None = None,
) -> App.DocumentObject:
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "EngineeringRole", "CompactInVacuum")
    obj.EngineeringRole = role
    if material is not None:
        obj.addProperty("App::PropertyString", "MaterialName", "CompactInVacuum")
        obj.MaterialName = material
    _document_group(doc, group_name).addObject(obj)

    view = getattr(obj, "ViewObject", None)
    if view is not None:
        view.Visibility = role in VISIBLE_BY_DEFAULT
        view.ShapeColor = _shape_color(name, role)
        view.LineColor = (0.12, 0.12, 0.12)
        view.Transparency = _transparency(name, role)
    return obj


def finalize_document(doc: App.Document) -> None:
    doc.recompute()
    if not App.GuiUp:
        return
    import FreeCADGui as Gui

    gui_doc = Gui.getDocument(doc.Name)
    if gui_doc is None:
        return
    view = gui_doc.activeView()
    view.viewAxonometric()
    view.fitAll()
    Gui.updateGui()
