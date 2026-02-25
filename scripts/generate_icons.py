#!/usr/bin/env python3
"""Generate icon.png (Linux) and icon.icns (macOS) from icon.ico.

Run once from the repo root:
    python scripts/generate_icons.py
"""

import tempfile
from pathlib import Path

from PIL import Image

import icnsutil

ROOT = Path(__file__).parent.parent
SRC = ROOT / "icon.ico"

# macOS ICNS role identifiers mapped to pixel sizes
ICNS_ROLES = [
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
]


def generate_png() -> None:
    """Save a 512x512 PNG for Linux PyInstaller builds."""
    with Image.open(SRC) as img:
        img = img.convert("RGBA")
        img = img.resize((512, 512), Image.LANCZOS)
        img.save(ROOT / "icon.png")
    print("Generated icon.png (512x512)")


def generate_icns() -> None:
    """Build a multi-size ICNS file for macOS PyInstaller builds."""
    icns = icnsutil.IcnsFile()
    with tempfile.TemporaryDirectory() as tmpdir:
        with Image.open(SRC) as img:
            img = img.convert("RGBA")
            for role, size in ICNS_ROLES:
                resized = img.resize((size, size), Image.LANCZOS)
                tmp_path = Path(tmpdir) / f"icon_{size}.png"
                resized.save(tmp_path)
                icns.add_media(role, file=str(tmp_path))
    icns.write(str(ROOT / "icon.icns"))
    print("Generated icon.icns")


if __name__ == "__main__":
    generate_png()
    generate_icns()
