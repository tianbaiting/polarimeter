from __future__ import annotations

import argparse
import importlib.util
import sys


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _required_modules(layer: str) -> list[str]:
    if layer == "pure_python":
        return ["pytest", "yaml"]
    if layer == "freecad_runtime":
        return ["pytest", "yaml", "FreeCAD"]
    raise ValueError(f"Unsupported layer: {layer}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dependency precheck for layered test execution.")
    parser.add_argument(
        "--layer",
        required=True,
        choices=("pure_python", "freecad_runtime"),
        help="Test layer name.",
    )
    args = parser.parse_args(argv)

    missing = [module for module in _required_modules(args.layer) if not _has_module(module)]
    if not missing:
        print(f"precheck: layer={args.layer} status=ok")
        return 0

    print(f"precheck: layer={args.layer} status=missing")
    for module in missing:
        if module == "yaml":
            print("missing module: yaml (install package: PyYAML)")
        else:
            print(f"missing module: {module}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
