from .config import BuildConfig, GeometryConfig, LayoutConfig, OutputConfig, load_build_config

__all__ = [
    "BuildConfig",
    "GeometryConfig",
    "LayoutConfig",
    "OutputConfig",
    "load_build_config",
]

# [EN] Export validation helpers only when the FreeCAD-backed runtime is available, so config/state tooling can still import the package on lighter environments. / [CN] 仅在 FreeCAD 运行时可用时导出校验辅助接口，使配置/状态工具在轻量环境下仍可导入本包。
try:
    from .validation import ValidationThresholds, validate_constraints
except ModuleNotFoundError:  # pragma: no cover - optional when FreeCAD runtime is unavailable
    pass
else:
    __all__.extend(
        [
            "ValidationThresholds",
            "validate_constraints",
        ]
    )
