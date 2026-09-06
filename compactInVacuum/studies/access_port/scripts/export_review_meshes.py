from __future__ import annotations

import argparse
from pathlib import Path

import FreeCAD as App
import Mesh

VISIBLE_ROLES = {"physical", "purchased_component_interface"}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    module_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--include-review-context", action="store_true")
    parser.add_argument(
        "--study-root",
        type=Path,
        default=module_root / "artifacts" / "access_port_study",
    )
    return parser.parse_args(argv)


def _group_name(obj) -> str:
    name = str(obj.Name)
    if name.startswith("MaintenanceAccess"):
        return "access"
    if name.endswith("ReservedModuleEnvelope"):
        return "neighbors"
    if name.startswith(("Capture", "Handling")):
        return "tools"
    if name.startswith(
        (
            "Carrier",
            "GripFork",
            "GripTrunnion",
            "FrontBraceAttachment",
            "RearBraceAttachment",
        )
    ):
        return "carrier"
    if name.endswith("ActivePlastic"):
        return "active"
    if name.endswith("LightTightSleeve"):
        return "housings"
    if name.startswith(("AnnularSupport", "DockPin")):
        return "support"
    if name == "CommonOpenSupportFrame" or name.endswith(
        ("PermanentWallSupport", "FrameSocket")
    ):
        return "support"
    if name.startswith(("ProjectChamberBody", "Front", "Rear")):
        return "chamber"
    if "WeldCollar" in name or "FeedthroughEnvelope" in name:
        return "services"
    return "internals"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    study_root = args.study_root.resolve()
    if (args.source is None) != (args.output_dir is None):
        raise ValueError("--source and --output-dir must be supplied together")
    entries = (
        [(args.source.resolve(), args.output_dir.resolve())]
        if args.source
        else [
            (
                study_root
                / standard.lower()
                / f"CompactOne_afterSRC_access_{standard}.FCStd",
                study_root / standard.lower() / "review_meshes",
            )
            for standard in ("ICF253", "ICF305", "ICF356")
        ]
    )
    for source, mesh_dir in entries:
        mesh_dir.mkdir(parents=True, exist_ok=True)
        document = App.openDocument(str(source))
        groups: dict[str, list[object]] = {
            "chamber": [],
            "access": [],
            "support": [],
            "services": [],
            "internals": [],
            "carrier": [],
            "tools": [],
            "neighbors": [],
            "active": [],
            "housings": [],
        }
        for obj in document.Objects:
            if not hasattr(obj, "Shape") or not hasattr(obj, "EngineeringRole"):
                continue
            if str(obj.EngineeringRole) not in VISIBLE_ROLES and not (
                args.include_review_context
                and str(obj.Name).endswith("ReservedModuleEnvelope")
            ):
                continue
            if obj.Shape.isNull():
                continue
            groups[_group_name(obj)].append(obj)
        for group_name, objects in groups.items():
            if not objects:
                continue
            destination = mesh_dir / f"{group_name}.stl"
            Mesh.export(objects, str(destination))
            print(destination)
        App.closeDocument(document.Name)
    # [EN] Review meshes preserve physical/purchased envelopes only; keepouts and physics overlays remain authoritative in FCStd and JSON. / [CN] 审图网格仅保留实体和采购包络；禁入区与物理叠加层仍以 FCStd 和 JSON 为准。
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
