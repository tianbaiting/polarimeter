from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

import FreeCAD as App

from .assembly import (
    build_cassette_document,
    build_sector_document,
    build_serviced_internal_document,
)
from .config import CIVConfig, load_config
from .export import export_fcstd, export_step


def _bounds(shape) -> dict[str, float]:
    box = shape.BoundBox
    return {
        "xmin_mm": float(box.XMin),
        "xmax_mm": float(box.XMax),
        "ymin_mm": float(box.YMin),
        "ymax_mm": float(box.YMax),
        "zmin_mm": float(box.ZMin),
        "zmax_mm": float(box.ZMax),
        "x_length_mm": float(box.XLength),
        "y_length_mm": float(box.YLength),
        "z_length_mm": float(box.ZLength),
    }


def document_geometry_metrics(
    cfg: CIVConfig,
    doc: App.Document,
    artifact_kind: str,
) -> dict[str, object]:
    objects: list[dict[str, object]] = []
    role_counts: Counter[str] = Counter()
    total_solid_count = 0
    physical_component_volume_mm3 = 0.0
    for obj in doc.Objects:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        role = (
            str(obj.EngineeringRole)
            if hasattr(obj, "EngineeringRole")
            else "unclassified"
        )
        material = (
            str(obj.MaterialName)
            if hasattr(obj, "MaterialName")
            else "not_applicable"
        )
        solid_count = len(obj.Shape.Solids)
        role_counts[role] += 1
        total_solid_count += solid_count
        if role == "physical":
            physical_component_volume_mm3 += float(obj.Shape.Volume)
        objects.append(
            {
                "name": obj.Name,
                "label": obj.Label,
                "engineering_role": role,
                "material": material,
                "shape_type": obj.Shape.ShapeType,
                "solid_count": solid_count,
                "volume_mm3": float(obj.Shape.Volume),
                "bounding_box": _bounds(obj.Shape),
            }
        )
    return {
        "schema_version": 1,
        "artifact_kind": artifact_kind,
        "deployment_profile": cfg.compact_one.deployment.name,
        "document_name": doc.Name,
        "object_count": len(objects),
        "role_counts": dict(sorted(role_counts.items())),
        "solid_count": total_solid_count,
        "physical_component_volume_sum_mm3": physical_component_volume_mm3,
        "objects": objects,
        "software": {
            "freecad_version": ".".join(App.Version()[:3]),
            "python_version": sys.version,
        },
    }


def _export_document_set(
    cfg: CIVConfig,
    doc: App.Document,
    output_dir: Path,
    basename: str,
    artifact_kind: str,
) -> dict[str, str]:
    fcstd = export_fcstd(doc, str(output_dir), basename)
    step = export_step(doc, str(output_dir), basename)
    metrics_path = output_dir / f"{basename}.geometry_metrics.json"
    metrics_path.write_text(
        json.dumps(
            document_geometry_metrics(cfg, doc, artifact_kind),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "fcstd": fcstd,
        "step": step,
        "metrics_json": str(metrics_path),
    }


def generate_prototype_artifacts(
    cfg: CIVConfig,
    output_dir: str | Path,
) -> dict[str, dict[str, str]]:
    if cfg.compact_one is None:
        raise ValueError("prototype artifacts require a CompactOne schema-v2 configuration")
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    builders = (
        (
            "golden_cassette",
            "CompactOne_golden_cassette",
            lambda: build_cassette_document(cfg),
        ),
        (
            "golden_sector",
            "CompactOne_golden_sector",
            lambda: build_sector_document(cfg, "left"),
        ),
        (
            "four_sector_internal",
            "CompactOne_four_sector_internal",
            lambda: build_serviced_internal_document(cfg),
        ),
    )
    artifacts: dict[str, dict[str, str]] = {}
    for artifact_kind, basename, builder in builders:
        doc = builder()
        artifacts[artifact_kind] = _export_document_set(
            cfg,
            doc,
            destination,
            basename,
            artifact_kind,
        )
    return artifacts


def main(config_path: str, output_dir: str) -> int:
    cfg = load_config(config_path)
    print(
        json.dumps(
            generate_prototype_artifacts(cfg, output_dir),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0
