"""Private local development persistence. One process coordinates profile writes."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from threading import RLock

LOCK = RLock()

# When set (use_atlas), profiles and plans are stored in MongoDB Atlas instead of
# local JSON files. storage_dir is then ignored. Local JSON stays the fallback.
_atlas = None


def use_atlas(database) -> None:
    """Route profile/plan persistence to Atlas using an injected PyMongo Database."""
    global _atlas
    from .atlas_store import AtlasAcademicStore

    _atlas = AtlasAcademicStore(database) if database is not None else None


def _user_folder(storage_dir: Path, user_id: str) -> Path:
    if not user_id:
        raise ValueError("a user id is required")
    digest = hashlib.sha256(user_id.encode()).hexdigest()[:16]
    return storage_dir / "profiles" / digest


def latest_revision(storage_dir: Path, user_id: str) -> int:
    return (load_profile(storage_dir, user_id) or {}).get("revision", 0)


def write_json(path: Path, value) -> Path:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as output:
        temp = Path(output.name)
        try:
            json.dump(value, output, indent=2)
            output.close()
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
    return path


def save_profile(
    storage_dir: Path, user_id: str, profile: dict, *, reimport=False, publication_guard=None
) -> Path:
    if profile.get("user_id") != user_id:
        raise PermissionError("profile owner mismatch")
    with LOCK:
        if reimport:
            from .corrections import restore_corrections

            profile["revision"] = latest_revision(storage_dir, user_id) + 1
            restore_corrections(storage_dir, user_id, profile)
        if _atlas is not None:
            _atlas.save_profile(user_id, profile, publication_guard=publication_guard)
            return storage_dir
        if publication_guard is not None and not publication_guard():
            raise PermissionError("import no longer authorized")
        folder = _user_folder(storage_dir, user_id)
        write_json(folder / f"profile-{profile['revision']}.json", profile)
        return write_json(folder / "profile.json", profile)


def load_profile(storage_dir: Path, user_id: str) -> dict | None:
    if _atlas is not None:
        return _atlas.load_profile(user_id)
    path = _user_folder(storage_dir, user_id) / "profile.json"
    if not path.exists():
        return None
    profile = json.loads(path.read_text(encoding="utf-8"))
    return profile if profile.get("user_id") == user_id else None


def save_plans(storage_dir: Path, user_id: str, plans: list[dict]) -> Path:
    if any(plan.get("user_id") != user_id for plan in plans):
        raise PermissionError("plan owner mismatch")
    if _atlas is not None:
        _atlas.save_plans(user_id, plans)
        return storage_dir
    return write_json(_user_folder(storage_dir, user_id) / "plans.json", plans)


def load_plans(storage_dir: Path, user_id: str) -> list[dict]:
    if _atlas is not None:
        return _atlas.load_plans(user_id)
    path = _user_folder(storage_dir, user_id) / "plans.json"
    if not path.exists():
        return []
    return [
        plan
        for plan in json.loads(path.read_text(encoding="utf-8"))
        if plan.get("user_id") == user_id
    ]
