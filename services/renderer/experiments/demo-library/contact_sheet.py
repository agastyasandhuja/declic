"""Inspection aid only; does not mark the frames or movie reviewed."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
index = json.loads((args.output / "frame-index.json").read_text())
width, height, columns = 240, 427, 3
sheet = Image.new(
    "RGB", (width * columns, (height + 28) * ((len(index) + 2) // 3)), "#192331"
)
draw = ImageDraw.Draw(sheet)
for i, entry in enumerate(index):
    with Image.open(args.output / entry["file"]) as source:
        frame = source.convert("RGB").resize((width, height))
    x, y = (i % columns) * width, (i // columns) * (height + 28)
    sheet.paste(frame, (x, y))
    draw.text(
        (x + 8, y + height + 6), f"{entry['file']}  {entry['time']:.2f}s", fill="white"
    )
sheet.save(args.output / "contact-sheet.jpg", quality=90)
print(args.output / "contact-sheet.jpg")
