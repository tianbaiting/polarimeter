#!/usr/bin/env python3
"""Build or check the documentation reading registry. / 构建或检查文档阅读清单。"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess


DOCS = Path(__file__).resolve().parents[1] / "docs"
ENTRY = re.compile(r"^\\(LocalDocEntry|DocEntry)\{([^{}]+)\}\{([^{}]+)\}", re.MULTILINE)
READ = re.compile(r"\\Read\{([^{}]+)\}")
ENGINE = re.compile(r"^\\DocEngine\{([^{}]+)\}\{([^{}]+)\}", re.MULTILINE)


def registry() -> dict[str, Path]:
    entries: dict[str, Path] = {}
    known: set[str] = set()
    for kind, key, relative in ENTRY.findall((DOCS / "navigation.tex").read_text()):
        if key in known:
            raise ValueError(f"Duplicate document key: {key}")
        known.add(key)
        if not re.fullmatch(r"[a-z0-9-]+", key):
            raise ValueError(f"Invalid document key: {key}")
        source = (DOCS / relative).resolve()
        if not source.is_relative_to(DOCS) or not source.is_file():
            if kind == "LocalDocEntry" and source.is_relative_to(DOCS):
                print(f"Optional local document absent: {relative}")
                continue
            raise FileNotFoundError(source)
        entries[key] = source
    for guide in (DOCS / "index_zh.tex", DOCS / "index_en.tex"):
        unknown = set(READ.findall(guide.read_text())) - known
        if unknown:
            raise ValueError(f"Unknown document keys in {guide.name}: {sorted(unknown)}")
    for key, engine in ENGINE.findall((DOCS / "navigation.tex").read_text()):
        if key not in known or engine not in {"xelatex", "lualatex"}:
            raise ValueError(f"Invalid engine selection: {key} / {engine}")
    print(f"Navigation checked: {len(known)} entries, {len(entries)} available locally")
    return entries


def build(entries: dict[str, Path]) -> None:
    engines = dict(ENGINE.findall((DOCS / "navigation.tex").read_text()))
    reading = DOCS / "build" / "reading"
    reading.mkdir(parents=True, exist_ok=True)
    for key, source in entries.items():
        if source.suffix != ".tex":
            continue
        output = DOCS / "build" / "documents" / key
        output.mkdir(parents=True, exist_ok=True)
        # [EN] Isolate build outputs so existing drafts and published PDFs are preserved. / [CN] 隔离构建产物，保留既有草稿及成稿 PDF。
        with (output / "build.log").open("w") as log:
            result = subprocess.run(
                ["latexmk", f"-{engines.get(key, 'xelatex')}", "-interaction=nonstopmode", "-halt-on-error",
                 f"-outdir={output}", source.name],
                cwd=source.parent, stdout=log, stderr=subprocess.STDOUT, check=False,
            )
        if result.returncode:
            raise RuntimeError(f"Build failed for {key}; see {output / 'build.log'}")
        shutil.copy2(output / f"{source.stem}.pdf", reading / f"{key}.pdf")
        print(f"Built reading copy: {key}.pdf", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--build", action="store_true")
    args = parser.parse_args()
    entries = registry()
    if args.build:
        build(entries)


if __name__ == "__main__":
    main()
