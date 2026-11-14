import hashlib
import json
import os
import subprocess
from pathlib import Path


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False))
    os.replace(tmp, path)


def run(args, timeout=120, **kwargs):
    return subprocess.run(
        [str(x) for x in args], check=True, capture_output=True, timeout=timeout, **kwargs
    )


def probe(path: Path):
    result = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path])
    return json.loads(result.stdout)


def contained(root: Path, relative: str):
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError("Invalid staged asset path")
    resolved = (root / p).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()) or (root / p).is_symlink():
        raise ValueError("Asset escapes staging root")
    return resolved
