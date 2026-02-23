#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_ROOTS = [REPO_ROOT / "dpolarization_archive"]
JUPYTEXT_BASE_CMD: list[str] | None = None


def run_cmd(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def resolve_jupytext_cmd() -> list[str]:
    if shutil.which("jupytext"):
        return ["jupytext"]
    if shutil.which("micromamba"):
        return ["micromamba", "run", "-n", "anaroot-env", "jupytext"]
    raise RuntimeError(
        "jupytext is not available. Install it or make sure micromamba env "
        "'anaroot-env' exists and contains jupytext."
    )


def run_jupytext(*args: str) -> None:
    global JUPYTEXT_BASE_CMD
    if JUPYTEXT_BASE_CMD is None:
        JUPYTEXT_BASE_CMD = resolve_jupytext_cmd()

    env = dict(os.environ)
    env.setdefault("XDG_CACHE_HOME", "/tmp")

    result = subprocess.run(
        [*JUPYTEXT_BASE_CMD, *args],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=[*JUPYTEXT_BASE_CMD, *args],
            output=result.stdout,
            stderr=result.stderr,
        )


def relpath(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def is_under_notebook_roots(path: Path) -> bool:
    for root in NOTEBOOK_ROOTS:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def is_notebook_py(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    try:
        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index > 160:
                    break
                if "jupytext:" in line or line.startswith("# %%"):
                    return True
    except OSError:
        return False
    return False


def gather_staged_files() -> list[Path]:
    output = run_cmd(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    ).strip()
    if not output:
        return []
    files: list[Path] = []
    for line in output.splitlines():
        path = (REPO_ROOT / line).resolve()
        if path.exists():
            files.append(path)
    return files


def gather_all_files() -> list[Path]:
    files: list[Path] = []
    for root in NOTEBOOK_ROOTS:
        if not root.exists():
            continue
        for ipynb in root.rglob("*.ipynb"):
            files.append(ipynb.resolve())
        for py_file in root.rglob("*.py"):
            py_path = py_file.resolve()
            if is_notebook_py(py_path):
                files.append(py_path)
    return files


def as_targets(paths: Iterable[Path]) -> list[Path]:
    targets: dict[str, Path] = {}
    for raw_path in paths:
        path = raw_path.resolve()
        if not path.exists():
            continue
        if not is_under_notebook_roots(path):
            continue
        if path.suffix not in {".ipynb", ".py"}:
            continue
        if path.suffix == ".py" and not (
            is_notebook_py(path) or path.with_suffix(".ipynb").exists()
        ):
            continue
        targets[str(path)] = path
    return list(targets.values())


def sync_target(path: Path) -> Path | None:
    if path.suffix == ".ipynb":
        pair_path = path.with_suffix(".py")
    else:
        pair_path = path

    run_jupytext("--set-formats", "ipynb,py:percent", relpath(path))
    run_jupytext("--sync", relpath(path))

    if pair_path.exists() and pair_path.suffix == ".py":
        return pair_path
    return None


def stage_files(paths: Iterable[Path]) -> None:
    unique = sorted({relpath(path) for path in paths if path.exists()})
    if not unique:
        return
    subprocess.run(["git", "add", *unique], cwd=REPO_ROOT, check=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync notebook ipynb/py pairs with jupytext."
    )
    parser.add_argument("paths", nargs="*", help="Paths to sync")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Sync all notebooks under tracked notebook roots",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Sync paths currently staged in git",
    )
    parser.add_argument(
        "--stage-updated",
        action="store_true",
        help="Stage generated or updated .py files",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if not any(root.exists() for root in NOTEBOOK_ROOTS):
        return 0

    input_paths: list[Path] = []
    if args.staged:
        input_paths.extend(gather_staged_files())
    if args.all:
        input_paths.extend(gather_all_files())
    if args.paths:
        input_paths.extend((REPO_ROOT / path).resolve() for path in args.paths)

    targets = as_targets(input_paths)
    if not targets:
        return 0

    updated_py: list[Path] = []
    for target in sorted(targets):
        try:
            updated = sync_target(target)
            if updated is not None:
                updated_py.append(updated)
        except RuntimeError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        except subprocess.CalledProcessError as exc:
            if exc.stderr:
                sys.stderr.write(exc.stderr)
            return exc.returncode

    if args.stage_updated:
        stage_files(updated_py)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
