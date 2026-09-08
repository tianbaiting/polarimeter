#!/usr/bin/env python3
"""Reproduce cited PDF crops with Poppler. / 使用 Poppler 复现引用的 PDF 截图。"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "sources.json").read_text())
    for source in manifest["sources"]:
        path = (ROOT / source["file"]).resolve()
        if not path.exists():
            if args.verify_only:
                raise FileNotFoundError(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            request = urllib.request.Request(source["url"], headers={"User-Agent": "polarimeter-reference-capture/1.0"})
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            if not payload.startswith(b"%PDF"):
                raise ValueError(f"Not a PDF: {source['url']}")
            if hashlib.sha256(payload).hexdigest() != source["sha256"]:
                raise ValueError(f"Source version changed: {source['id']}")
            path.write_bytes(payload)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source["sha256"]:
            raise ValueError(f"Source hash mismatch: {source['id']}")
        for crop in source["crops"]:
            destination = ROOT / "figures" / crop["image"]
            if args.verify_only:
                if not destination.is_file():
                    raise FileNotFoundError(destination)
                continue
            page = str(crop["pdf_page"])
            info = subprocess.check_output(["pdfinfo", "-f", page, "-l", page, str(path)], text=True)
            match = re.search(r"(?:Page\s+\d+\s+size|Page size):\s+([\d.]+) x ([\d.]+)", info)
            if not match:
                raise ValueError(f"Cannot read page dimensions: {path}")
            width, height = (float(value) for value in match.groups())
            scale = manifest["dpi"] / 72
            x0, y0, x1, y1 = crop["box_fraction_top_left"]
            x, y = math.floor(x0 * width * scale), math.floor(y0 * height * scale)
            w, h = math.ceil((x1 - x0) * width * scale), math.ceil((y1 - y0) * height * scale)
            destination.parent.mkdir(parents=True, exist_ok=True)
            # [EN] Preserve source pixels and isolate temporary outputs until rendering succeeds. / [CN] 保留原始图像内容，渲染成功前隔离临时输出。
            with tempfile.TemporaryDirectory(prefix="polarization-crop-") as temporary:
                prefix = Path(temporary) / "crop"
                subprocess.run(["pdftoppm", "-f", page, "-l", page, "-r", str(manifest["dpi"]),
                                "-x", str(x), "-y", str(y), "-W", str(w), "-H", str(h),
                                "-singlefile", "-png", str(path), str(prefix)], check=True)
                destination.write_bytes(prefix.with_suffix(".png").read_bytes())
        print(f"Verified {source['id']}: {digest}")


if __name__ == "__main__":
    main()
