"""Bounded inventory and text extraction for student-visible Canvas resources."""
from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from itertools import islice
from pathlib import PurePosixPath
from urllib.parse import quote
from xml.etree import ElementTree

from ..client.http import CanvasAuthError, CanvasClient, CanvasError

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_RESOURCE_ITEMS = 100
FILE_MEDIA = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}
READABLE_FILES = {".txt", ".md", ".csv", ".pptx", *FILE_MEDIA}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0
        self.file_ids = set()

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template"}:
            self.hidden += 1
        if not self.hidden:
            self.parts.append("\n" if tag in {"br", "p", "li", "tr", "div"} else " ")
            for name, value in attrs:
                if name in {"href", "src", "data-api-endpoint"} and value:
                    match = re.search(r"/files/(\d+)(?:[/?#]|$)", value)
                    if match:
                        self.file_ids.add(match[1])

    def handle_endtag(self, tag):
        if tag in {"script", "style", "template"} and self.hidden:
            self.hidden -= 1
        if not self.hidden:
            self.parts.append("\n" if tag in {"br", "p", "li", "tr", "div"} else " ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def parse_html(value):
    parser = _Text()
    parser.feed(value if isinstance(value, str) else "")
    parser.close()
    return "\n".join(clean for line in "".join(parser.parts).splitlines()
                     if (clean := " ".join(line.split()))), parser.file_ids


@dataclass(frozen=True)
class Resource:
    external_id: str
    kind: str
    title: str
    text: str | None
    updated_at: str | None = None
    locator: str = "whole source"
    content_hash: str | None = None
    download_url: str | None = None


def _file_text(suffix, data):
    if suffix in {".txt", ".md", ".csv"}:
        return data.decode("utf-8-sig")
    if suffix == ".pptx":
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            slides = sorted(
                (entry for entry in archive.infolist()
                 if re.fullmatch(r"ppt/slides/slide\d+\.xml", entry.filename)),
                key=lambda entry: int(re.search(r"(\d+)\.xml", entry.filename)[1]),
            )
            if len(slides) > 200 or sum(entry.file_size for entry in slides) > MAX_FILE_BYTES:
                return None
            return "\n".join(
                "Slide " + re.search(r"(\d+)\.xml", entry.filename)[1] + ": " +
                " ".join(node.text for node in ElementTree.fromstring(archive.read(entry)).iter()
                         if node.tag == "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
                         and node.text)
                for entry in slides[:40]
            )
    if suffix == ".pdf" and data.startswith(b"%PDF-"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data), strict=True)
            return "\n".join(
                f"Page {index}: {page.extract_text() or ''}"
                for index, page in enumerate(islice(reader.pages, 20), 1)
            )
        except Exception:
            # Optional parser, encrypted/corrupt PDF, or unsupported encoding.
            return None
    return None


def _items(client, path, missing, label, params=None, limit=MAX_RESOURCE_ITEMS):
    try:
        for index, row in enumerate(client.paginate(path, params)):
            if index == limit:
                missing.add(f"{label}: inventory limited")
                return
            if isinstance(row, dict) and row.get("published") is not False:
                yield row
    except CanvasAuthError:
        raise
    except CanvasError:
        missing.add(f"{label}: unavailable")


def fetch_resources(client: CanvasClient, course_id: str, syllabus_files=(), *, today=None):
    base = f"/api/v1/courses/{quote(course_id, safe='')}"
    sources, missing = [], set()
    page_slugs, file_ids = {}, dict.fromkeys(sorted(syllabus_files))
    page_modules, file_modules = {}, {}
    for module in _items(client, f"{base}/modules", missing, "modules", limit=40):
        module_id = module.get("id")
        if module_id is None or module.get("locked_for_user"):
            continue
        name = str(module.get("name") or "")
        titles = []
        for item in _items(client, f"{base}/modules/{quote(str(module_id), safe='')}/items", missing, "module items"):
            if item.get("locked_for_user"):
                continue
            titles.append(str(item.get("title") or ""))
            if item.get("type") == "Page" and item.get("page_url"):
                slug = str(item["page_url"])
                page_slugs.setdefault(slug, None)
                page_modules.setdefault(slug, []).append(name)
            if item.get("type") == "File" and item.get("content_id") is not None:
                file_id = str(item["content_id"])
                file_ids.setdefault(file_id, None)
                file_modules.setdefault(file_id, []).append(name)
        sources.append(Resource(str(module_id), "module", name, "\n".join([name, *titles]),
                                module.get("updated_at"), "ordered module outline"))
    for page in _items(client, f"{base}/pages", missing, "pages"):
        if page.get("url") and not page.get("locked_for_user"):
            page_slugs[str(page["url"])] = page
    if len(page_slugs) > 50:
        missing.add("pages: excerpt inventory limited")
    for slug, page in islice(page_slugs.items(), 50):
        try:
            if page is None or "body" not in page:
                page = client.get(f"{base}/pages/{quote(slug, safe='')}")
        except CanvasAuthError:
            raise
        except CanvasError:
            missing.add("page: unavailable")
            continue
        if not isinstance(page, dict) or page.get("locked_for_user") or page.get("published") is False:
            continue
        excerpt, links = parse_html(page.get("body"))
        file_ids.update(dict.fromkeys(sorted(links)))
        sources.append(Resource(str(page.get("page_id") or slug), "page", str(page.get("title") or ""),
                                excerpt, page.get("updated_at"), ", ".join(page_modules.get(slug, [])) or "page body"))

    files = {str(row["id"]): row for row in _items(client, f"{base}/files", missing, "files")
             if row.get("id") is not None}
    file_ids.update(dict.fromkeys(files))
    if len(file_ids) > MAX_RESOURCE_ITEMS:
        missing.add("files: inventory limited")
    for file_id in islice(file_ids, MAX_RESOURCE_ITEMS):
        try:
            row = files.get(file_id)
            if row is None:
                row = client.get(f"{base}/files/{quote(file_id, safe='')}")
            if (not isinstance(row, dict) or row.get("locked_for_user")
                    or row.get("hidden_for_user") or row.get("published") is False):
                missing.add("file: unavailable")
                continue
            title = str(row.get("display_name") or row.get("filename") or "")
            suffix = PurePosixPath(title).suffix.lower()
            url = row.get("url")
            readable = (suffix in READABLE_FILES and isinstance(url, str) and bool(url)
                        and (not isinstance(row.get("size"), int) or row["size"] <= MAX_FILE_BYTES))
            if not readable:
                missing.add("file: some formats or sizes unsupported")
            sources.append(Resource(file_id, "file", title, None, row.get("updated_at"),
                                    ", ".join(file_modules.get(file_id, [])) or "document",
                                    download_url=url if readable else None))
        except CanvasAuthError:
            raise
        except CanvasError:
            missing.add("file: unavailable")

    today = today or datetime.now(timezone.utc).date()
    dates = [("context_codes[]", f"course_{course_id}"), ("type", "event"),
             ("start_date", str(today - timedelta(days=180))),
             ("end_date", str(today + timedelta(days=180)))]
    for event in _items(client, "/api/v1/calendar_events", missing, "calendar", dates):
        if (event.get("id") is None or event.get("context_code") != f"course_{course_id}"
                or event.get("workflow_state") == "deleted"):
            continue
        name = str(event.get("title") or "")
        start = event.get("all_day_date") if event.get("all_day") else event.get("start_at")
        description, _ = parse_html(event.get("description"))
        text = f"Event: {name}\nScheduled: {start or 'undated'}\n{description}"
        sources.append(Resource(str(event["id"]), "calendar_event", name, text,
                                event.get("updated_at"), "calendar event"))
    return sources, sorted(missing)
