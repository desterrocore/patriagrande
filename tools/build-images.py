#!/usr/bin/env python3
"""
Derive every image the site ships from the originals in reference-content/.

The originals are large (a 9 MB portrait, a 6000 px event photo) and are
deliberately kept out of the published artifact. This script is the only thing
that writes into assets/img/, so the published images are always reproducible
from source/images.json — no hand-cropped file ever becomes load-bearing.

    python3 tools/build-images.py            # build everything
    python3 tools/build-images.py --check    # verify outputs match the manifest
    python3 tools/build-images.py equipe     # build one group only

Requires Pillow, and pillow-heif for the one .HEIC original:

    python3 -m pip install Pillow pillow-heif
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # only one source file needs it
    pass

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "source" / "images.json"
OUT_ROOT = ROOT / "assets" / "img"

# Quality is set per format rather than per image. WebP at 80 and JPEG at 82
# are visually indistinguishable from the source at these display sizes, and
# the whole assets/img tree stays well under a megabyte and a half.
WEBP_Q = 80
JPEG_Q = 82


def crop_to_ratio(im: Image.Image, ratio: float, focus_y: float, focus_x: float) -> Image.Image:
    """Crop to `ratio` (w/h), keeping the point at (focus_x, focus_y) in frame.

    Focus is expressed in 0..1 of the source dimensions. The default of 0.5
    centres; portraits usually want a lower focus_y so the crop keeps the head
    rather than slicing it off the top.
    """
    w, h = im.size
    if w / h > ratio:
        new_w = round(h * ratio)
        left = round(focus_x * w - new_w / 2)
        left = max(0, min(left, w - new_w))
        box = (left, 0, left + new_w, h)
    else:
        new_h = round(w / ratio)
        top = round(focus_y * h - new_h / 2)
        top = max(0, min(top, h - new_h))
        box = (0, top, w, top + new_h)
    return im.crop(box)


def build_one(entry: dict, group: str, check: bool) -> list[str]:
    src = ROOT / entry["src"]
    if not src.exists():
        raise SystemExit(f"origem ausente: {src}")

    im = ImageOps.exif_transpose(Image.open(src))
    if im.mode != "RGB":
        im = im.convert("RGB")

    # Um original pode estar deitado sem carregar a tag EXIF que diria isso —
    # o retrato da Sara Borém é o caso. "rotate" é em graus no sentido
    # anti-horário, como no PIL.
    if entry.get("rotate"):
        im = im.rotate(int(entry["rotate"]), expand=True)

    # "box" é um recorte absoluto em pixels do original, para quando o rosto
    # está tão perto de uma borda que centrar por foco não resolve.
    if entry.get("box"):
        im = im.crop(tuple(int(v) for v in entry["box"]))

    ratio = entry.get("ratio")
    if ratio:
        num, den = (float(x) for x in str(ratio).split(":"))
        im = crop_to_ratio(
            im, num / den, float(entry.get("focus_y", 0.5)), float(entry.get("focus_x", 0.5))
        )

    out_dir = OUT_ROOT / group
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for width in entry["widths"]:
        if im.width < width:
            # Never upscale: a 780 px original stays 780 px and the srcset
            # simply has one fewer candidate.
            continue
        scaled = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        stem = entry["name"] if len(entry["widths"]) == 1 else f"{entry['name']}-{width}"
        for ext, kwargs in (
            ("webp", dict(format="WEBP", quality=WEBP_Q, method=6)),
            ("jpg", dict(format="JPEG", quality=JPEG_Q, optimize=True, progressive=True)),
        ):
            path = out_dir / f"{stem}.{ext}"
            if check:
                if not path.exists():
                    written.append(f"FALTANDO {path.relative_to(ROOT)}")
                continue
            scaled.save(path, **kwargs)
            written.append(str(path.relative_to(ROOT)))
    return written


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    check = "--check" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("-")]

    total = 0
    problems = []
    for group, entries in manifest.items():
        if only and group not in only:
            continue
        for entry in entries:
            for line in build_one(entry, group, check):
                if line.startswith("FALTANDO"):
                    problems.append(line)
                else:
                    total += 1
                    print(line)

    if check:
        if problems:
            print("\n".join(problems), file=sys.stderr)
            print(f"\n{len(problems)} arquivo(s) ausente(s) — rode sem --check.", file=sys.stderr)
            return 1
        print("Todas as imagens do manifesto estão presentes.")
        return 0

    print(f"\n{total} arquivo(s) gerado(s) em assets/img/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
