from __future__ import annotations

from pathlib import Path

import Part

from .config import OutputConfig


def export_document(
    doc,
    export_objects,
    output_cfg: OutputConfig,
) -> dict[str, Path]:
    output_cfg.output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    if "fcstd" in output_cfg.formats:
        fcstd_path = output_cfg.output_dir / f"{output_cfg.basename}.FCStd"
        doc.saveAs(str(fcstd_path))
        paths["fcstd"] = fcstd_path

    if "step" in output_cfg.formats:
        step_path = output_cfg.output_dir / f"{output_cfg.basename}.step"
        Part.export(export_objects, str(step_path))
        paths["step"] = step_path

    return paths
