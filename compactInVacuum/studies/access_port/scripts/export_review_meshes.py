from __future__ import annotations

import argparse
from pathlib import Path

import FreeCAD as App
import Mesh


VISIBLE_ROLES = {"physical", "purchased_component_interface"}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    module_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
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
    if name.endswith("PermanentWallSupport"):
        return "support"
    if name.startswith(("ProjectChamberBody", "Front", "Rear")):
        return "chamber"
    if "WeldCollar" in name or "FeedthroughEnvelope" in name:
        return "services"
    return "internals"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    study_root = args.study_root.resolve()
    for standard in ("ICF253", "ICF305", "ICF356"):
        token = standard.lower()
        source = (
            study_root
            / token
            / f"CompactOne_afterSRC_access_{standard}.FCStd"
        )
        mesh_dir = study_root / token / "review_meshes"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        document = App.openDocument(str(source))
        groups: dict[str, list[object]] = {
            "chamber": [],
            "access": [],
            "support": [],
            "services": [],
            "internals": [],
        }
        for obj in document.Objects:
            if not hasattr(obj, "Shape") or not hasattr(obj, "EngineeringRole"):
                continue
            if str(obj.EngineeringRole) not in VISIBLE_ROLES:
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
