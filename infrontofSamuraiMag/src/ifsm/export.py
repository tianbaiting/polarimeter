from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

import FreeCAD as App
import Part

from .config import OutputConfig


def ensure_fcstd_gui_session() -> None:
    if App.GuiUp:
        return

    try:
        import FreeCADGui as Gui
    except Exception as exc:  # pragma: no cover - exercised in FreeCAD runtime only
        raise RuntimeError(
            "FCStd export requires FreeCADGui so the saved archive includes GuiDocument.xml."
        ) from exc

    try:
        # [EN] Offscreen GUI initialization must happen before document creation so FreeCAD allocates GUI-side view providers and persists GuiDocument.xml with visibility/camera state. / [CN] 必须在建文档前初始化离屏 GUI，这样 FreeCAD 才会分配 GUI 侧 view provider，并把可见性/相机状态写入 GuiDocument.xml。
        Gui.showMainWindow()
    except Exception as exc:  # pragma: no cover - exercised in FreeCAD runtime only
        raise RuntimeError(
            "Failed to initialize the offscreen FreeCAD GUI session required for FCStd export."
        ) from exc

    if not App.GuiUp:  # pragma: no cover - exercised in FreeCAD runtime only
        raise RuntimeError("FreeCAD GUI session did not activate; FCStd export would miss GuiDocument.xml.")


def _prepare_fcstd_gui_state(doc) -> None:
    if not App.GuiUp:
        raise RuntimeError(
            "FCStd export requires the GUI session to be initialized before document creation."
        )

    try:
        import FreeCADGui as Gui
    except Exception as exc:  # pragma: no cover - exercised in FreeCAD runtime only
        raise RuntimeError("FreeCADGui became unavailable during FCStd export.") from exc

    # [EN] Review FCStd files should open with every generated solid already visible in the tree and viewport instead of inheriting whichever transient object was last hidden during automation. / [CN] 评审用 FCStd 打开时应让所有生成实体默认可见，而不是继承自动化过程中某个临时隐藏状态。
    for obj in doc.Objects:
        view_obj = getattr(obj, "ViewObject", None)
        if view_obj is None:
            continue
        try:
            view_obj.Visibility = True
        except Exception:
            pass
        if hasattr(view_obj, "ShowInTree"):
            try:
                view_obj.ShowInTree = True
            except Exception:
                pass

    gui_doc = Gui.getDocument(doc.Name) if hasattr(Gui, "getDocument") else Gui.activeDocument()
    if gui_doc is None:
        raise RuntimeError(f"Missing GUI document wrapper for {doc.Name}; cannot persist FCStd view state.")

    active_view = gui_doc.activeView()
    active_view.viewIsometric()
    active_view.fitAll()


def _verify_fcstd_archive(fcstd_path: Path) -> None:
    try:
        with ZipFile(fcstd_path) as archive:
            names = set(archive.namelist())
    except BadZipFile as exc:
        raise RuntimeError(f"FCStd archive is corrupt: {fcstd_path}") from exc

    if "Document.xml" not in names:
        raise RuntimeError(f"FCStd archive is missing Document.xml: {fcstd_path}")
    if "GuiDocument.xml" not in names:
        raise RuntimeError(f"FCStd archive is missing GuiDocument.xml: {fcstd_path}")


def _verify_fcstd_roundtrip(fcstd_path: Path, expected_object_names: list[str]) -> None:
    _verify_fcstd_archive(fcstd_path)
    try:
        verify_doc = App.openDocument(str(fcstd_path))
    except Exception as exc:  # pragma: no cover - exercised in FreeCAD runtime only
        raise RuntimeError(f"FCStd round-trip reopen failed for {fcstd_path}") from exc

    try:
        missing: list[str] = []
        null_shape: list[str] = []
        for name in expected_object_names:
            obj = verify_doc.getObject(name)
            if obj is None:
                missing.append(name)
                continue
            if not hasattr(obj, "Shape") or obj.Shape.isNull():
                null_shape.append(name)

        if missing or null_shape:
            detail: list[str] = []
            if missing:
                sample = ", ".join(missing[:8])
                suffix = " ..." if len(missing) > 8 else ""
                detail.append(f"missing=[{sample}{suffix}]")
            if null_shape:
                sample = ", ".join(null_shape[:8])
                suffix = " ..." if len(null_shape) > 8 else ""
                detail.append(f"null_shape=[{sample}{suffix}]")
            raise RuntimeError(
                f"FCStd round-trip validation failed for {fcstd_path}: {'; '.join(detail)}"
            )
    finally:
        App.closeDocument(verify_doc.Name)


def export_document(
    doc,
    export_objects,
    output_cfg: OutputConfig,
) -> dict[str, Path]:
    output_cfg.output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    doc.recompute()

    if "step" in output_cfg.formats:
        # [EN] STEP export flattens only the review/manufacturing solids so downstream CAD tools consume geometry without FreeCAD-specific document metadata. / [CN] STEP 只导出用于审查/制造的实体，使下游 CAD 工具直接消费几何而无需 FreeCAD 专有文档元数据。
        step_path = output_cfg.output_dir / f"{output_cfg.basename}.step"
        Part.export(export_objects, str(step_path))
        paths["step"] = step_path

    if "fcstd" in output_cfg.formats:
        # [EN] Save FCStd after STEP and immediately reload it to catch sandbox/config induced persistence faults before the pipeline reports success. / [CN] FCStd 放在 STEP 之后保存，并立即回读校验，以便在 pipeline 报告成功前捕获沙箱/配置目录导致的持久化故障。
        fcstd_path = output_cfg.output_dir / f"{output_cfg.basename}.FCStd"
        export_object_names = [obj.Name for obj in export_objects]
        doc_name = doc.Name
        _prepare_fcstd_gui_state(doc)
        doc.saveAs(str(fcstd_path))
        doc.save()
        App.closeDocument(doc_name)
        _verify_fcstd_roundtrip(fcstd_path, export_object_names)
        paths["fcstd"] = fcstd_path

    return paths
