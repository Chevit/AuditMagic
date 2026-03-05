#!/usr/bin/env python
"""Extract the largest frame from icon.ico and save as splash.png."""
from pathlib import Path
from PIL import Image

root = Path(__file__).parent.parent
ico_path = root / "icon.ico"
out_path = root / "splash.png"

img = Image.open(ico_path)
# ICO files contain multiple sizes; find the largest by pixel area
sizes = img.ico.sizes()
largest = max(sizes, key=lambda s: s[0] * s[1])
frame = img.ico.getimage(largest).convert("RGBA")

# Composite onto a solid background to eliminate transparency —
# PyInstaller's Tcl/Tk splash renders transparent pixels as magenta.
bg = Image.new("RGBA", frame.size, (40, 40, 40, 255))
bg.paste(frame, mask=frame)
bg.convert("RGB").save(out_path, "PNG")
print(f"Saved {largest[0]}x{largest[1]} frame to {out_path}")
