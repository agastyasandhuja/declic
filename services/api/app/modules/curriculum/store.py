"""Local profile persistence (owner: Amogh) — a stand-in for the Atlas academics
collections. Stores one versioned AcademicProfile document per user as JSON.
Replace with an Atlas-backed adapter once Agastya provisions the connection;
the record shape already follows contracts/academics.md.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _user_folder(storage_dir: Path, user_id: str) -> Path:
    digest = hashlib.sha256(user_id.encode()).hexdigest()[:16]
    return storage_dir / "profiles" / digest


def latest_revision(storage_dir: Path, user_id: str) -> int:
    path = _user_folder(storage_dir, user_id) / "profile.json"
    if not path.exists():
        return 0
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("revision", 0))
    except (ValueError, OSError):
        return 0


def save_profile(storage_dir: Path, user_id: str, profile: dict) -> Path:
    folder = _user_folder(storage_dir, user_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "profile.json"
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return path


def load_profile(storage_dir: Path, user_id: str) -> dict | None:
    path = _user_folder(storage_dir, user_id) / "profile.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
