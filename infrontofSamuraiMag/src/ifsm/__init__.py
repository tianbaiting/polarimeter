from .config import BuildConfig, GeometryConfig, LayoutConfig, OutputConfig, load_build_config

__all__ = [
    "BuildConfig",
    "GeometryConfig",
    "LayoutConfig",
    "OutputConfig",
    "load_build_config",
]

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
