"""Inspection aid only; does not mark the frames or movie reviewed."""

import argparse
import hashlib
import io
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
frame_hashes = {}
for i, entry in enumerate(index):
    data = (args.output / entry["file"]).read_bytes()
    frame_hashes[entry["file"]] = hashlib.sha256(data).hexdigest()
    with Image.open(io.BytesIO(data)) as source:
        frame = source.convert("RGB").resize((width, height))
    x, y = (i % columns) * width, (i // columns) * (height + 28)
    sheet.paste(frame, (x, y))
    draw.text(
        (x + 8, y + height + 6), f"{entry['file']}  {entry['time']:.2f}s", fill="white"
    )
temporary = args.output / "contact-sheet.tmp.jpg"
sheet.save(temporary, quality=90)
proof = json.loads((args.output / "stills-provenance.json").read_text())
for name, expected in frame_hashes.items():
    if hashlib.sha256((args.output / name).read_bytes()).hexdigest() != expected:
        raise ValueError("Frames changed while assembling the contact sheet")
temporary.replace(args.output / "contact-sheet.jpg")
metadata = {
    "provenance": {
        key: proof[key] for key in ("lesson_sha256", "pack_sha256", "renderer_source")
    },
    "frames": frame_hashes,
    "sheet_sha256": hashlib.sha256(
        (args.output / "contact-sheet.jpg").read_bytes()
    ).hexdigest(),
}
temp_proof = args.output / "contact-sheet-provenance.tmp.json"
temp_proof.write_text(json.dumps(metadata, indent=2))
temp_proof.replace(args.output / "contact-sheet-provenance.json")
print(args.output / "contact-sheet.jpg")
