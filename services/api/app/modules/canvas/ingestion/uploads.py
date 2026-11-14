"""Upload fallback: course-labeled files stored privately with demo provenance.

Used when live Canvas access is unavailable. Produces SourceDocument records
(contracts/academics.md) with resource_type "upload" and an explicit
provenance marker, so uploaded material is never mistaken for a live sync.

Storage here is a local private directory (default .local/academics, which is
gitignored). It is a stand-in until the shared private bucket exists.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_ZIP = b"PK\x03\x04"
# extension -> required leading bytes (None = must be UTF-8 text)
ALLOWED_TYPES: dict[str, bytes | None] = {
    ".pdf": b"%PDF-",
    ".pptx": _ZIP,
    ".docx": _ZIP,
    ".txt": None,
    ".md": None,
}


class UploadRejected(ValueError):
    pass


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]


def upload_course_id(user_id: str, course_label: str) -> str:
    label = re.sub(r"\s+", " ", course_label).strip().lower()
    if not label:
        raise UploadRejected("a course label is required for every upload")
    return f"crs_upl_{_digest(user_id, label)}"


def validate_upload(filename: str, data: bytes) -> str:
    """Return the normalized extension or raise UploadRejected."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        raise UploadRejected(f"unsupported file type {ext or '(none)'}; allowed: {allowed}")
    if not data:
        raise UploadRejected("file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadRejected(f"file exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")
    magic = ALLOWED_TYPES[ext]
    if magic is not None:
        if not data.startswith(magic):
            raise UploadRejected(f"file content does not match its {ext} extension")
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise UploadRejected("text upload is not valid UTF-8") from None
        if "\x00" in text:
            raise UploadRejected("text upload contains binary data")
    return ext


def _user_dir(storage_dir: Path, user_id: str) -> Path:
    return storage_dir / "uploads" / _digest(user_id)


def load_sources(user_id: str, storage_dir: Path) -> list[dict]:
    """Return the SourceDocument records this user has uploaded (may be empty)."""
    manifest = _user_dir(storage_dir, user_id) / "sources.json"
    if not manifest.exists():
        return []
    return [record for record in json.loads(manifest.read_text(encoding="utf-8"))
            if record.get("user_id") == user_id]


def read_text(record: dict, storage_dir: Path) -> str | None:
    """Return decoded text for a text/markdown upload, else None.

    Binary formats (pdf/pptx/docx) need an extraction dependency that is not
    installed yet; those return None until M2 adds real extraction.
    """
    ref = record.get("storage_ref", "")
    prefix = "local-private://uploads/"
    if not ref.startswith(prefix):
        return None
    rel = ref[len(prefix):]
    user_folder, _, blob = rel.partition("/")
    path = (storage_dir / "uploads" / user_folder / blob).resolve()
    # Stay strictly inside the upload store (defence against a tampered ref).
    if not record.get("user_id") or path.parent != _user_dir(storage_dir, record["user_id"]).resolve() or not path.is_file():
        return None
    if path.suffix.lower() not in (".txt", ".md"):
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def store_upload(
    *,
    user_id: str,
    course_label: str,
    filename: str,
    data: bytes,
    storage_dir: Path,
) -> tuple[dict, bool]:
    """Validate and store one file. Returns (SourceDocument, created).

    Re-uploading identical content for the same user and course returns the
    existing record with created=False.
    """
    if not user_id:
        raise UploadRejected("uploads must belong to an authenticated app user")
    ext = validate_upload(filename, data)
    course_id = upload_course_id(user_id, course_label)
    content_hash = hashlib.sha256(data).hexdigest()
    source_id = f"src_{_digest(user_id, course_id, content_hash)}"

    user_dir = storage_dir / "uploads" / _digest(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = user_dir / "sources.json"
    manifest: list[dict] = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    )
    for record in manifest:
        if record["source_id"] == source_id:
            return record, False

    # Stored under the content hash, so the client filename never becomes a path.
    blob_name = f"{content_hash}{ext}"
    (user_dir / blob_name).write_bytes(data)
    record = {
        "source_id": source_id,
        "user_id": user_id,
        "course_id": course_id,
        "external_id": None,
        "resource_type": "upload",
        "title": Path(filename).name[:200],
        "storage_ref": f"local-private://uploads/{user_dir.name}/{blob_name}",
        "content_hash": f"sha256:{content_hash}",
        "source_updated_at": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "scope": "private",
        "provenance": {
            "mode": "upload",
            "demo": True,
            "course_label": re.sub(r"\s+", " ", course_label).strip(),
        },
    }
    manifest.append(record)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return record, True
