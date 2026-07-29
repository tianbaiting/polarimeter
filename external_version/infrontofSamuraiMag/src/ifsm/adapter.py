from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .assembly import BuildResult, build_document
from .config import BuildConfig, OutputConfig, load_build_config
from .export import export_document
from .layout import DetectorPlacement, build_detector_placements
from .validation import ValidationReport, ValidationThresholds, validate_constraints


@dataclass(frozen=True)
class BuildArtifacts:
    placements: list[DetectorPlacement]
    exported_paths: dict[str, Path]


class BuildAdapter(Protocol):
    # [EN] The adapter boundary keeps CLI/stateflow independent from the concrete FreeCAD execution path, which is useful when validation-only or future remote builders reuse the same contract. / [CN] 适配器边界让 CLI/状态流不依赖具体 FreeCAD 执行路径，便于纯校验流程或未来远程构建复用同一契约。
    def load_config(self, config_path: Path, overrides: list[str]) -> BuildConfig: ...

    def build_model(self, cfg: BuildConfig, doc_name: str) -> BuildResult: ...

    def export_model(self, result: BuildResult, output_cfg: OutputConfig) -> dict[str, Path]: ...

    def build_layout_only(self, cfg: BuildConfig) -> list[DetectorPlacement]: ...

    def validate_constraints(
        self,
        cfg: BuildConfig,
        placements: list[DetectorPlacement],
        thresholds: ValidationThresholds,
    ) -> ValidationReport: ...


class LocalBuildAdapter:
    def load_config(self, config_path: Path, overrides: list[str]) -> BuildConfig:
        return load_build_config(config_path, overrides=overrides)

    def build_model(self, cfg: BuildConfig, doc_name: str) -> BuildResult:
        return build_document(cfg, doc_name=doc_name)

    def export_model(self, result: BuildResult, output_cfg: OutputConfig) -> dict[str, Path]:
        return export_document(result.document, result.export_objects, output_cfg)

    def build_layout_only(self, cfg: BuildConfig) -> list[DetectorPlacement]:
        # [EN] Validation-only mode still materializes the full analytical detector layout because angle/radius acceptance is defined on channel front-face centers before CAD solids exist. / [CN] 纯校验模式仍要生成完整解析探测器布局，因为角度/半径验收先定义在通道前端面中心上，再于 CAD 实体之前成立。
        return build_detector_placements(cfg.layout)

    def validate_constraints(
        self,
        cfg: BuildConfig,
        placements: list[DetectorPlacement],
        thresholds: ValidationThresholds,
    ) -> ValidationReport:
        return validate_constraints(placements, cfg.geometry, thresholds)
