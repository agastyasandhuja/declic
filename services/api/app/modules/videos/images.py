"""Model-directed search, trusted retrieval. The renderer receives local JPEGs only."""

import hashlib
import html
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .media import atomic_json, probe, run, sha256
from .models import digest

CDN_HOSTS = {"upload.wikimedia.org", "images-assets.nasa.gov", "live.staticflickr.com"}
MAX_IMAGE_BYTES = 12_000_000


def plain(value, limit=400):
    return html.unescape(re.sub(r"<[^>]*>", "", str(value or "")))[:limit]


def allowed_image_url(url):
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname not in CDN_HOSTS
        or parts.username
        or parts.password
        or parts.port not in (None, 443)
        or parts.fragment
    ):
        raise ValueError("Image URL is outside the approved image CDNs")
    return url


class ImageLibrary:
    def __init__(self, client=None):
        self.client = client or httpx.Client(
            timeout=30,
            follow_redirects=False,
            headers={"User-Agent": "HackUMassLearningVideo/0.2 (educational prototype)"},
        )
        self.candidates = {}

    def _json(self, url, params):
        for attempt in range(3):
            try:
                return self._read_json(url, params)
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 429 and error.response.status_code < 500:
                    raise
                if attempt == 2:
                    raise
            except (httpx.NetworkError, httpx.TimeoutException):
                if attempt == 2:
                    raise
            time.sleep(2**attempt)

    def _read_json(self, url, params):
        with self.client.stream("GET", url, params=params) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    raise ValueError("Image search response too large")
        import json

        return json.loads(body)

    def search(self, request):
        query = request.query.strip()
        if not 3 <= len(query) <= 120 or re.search(r"https?:|@|[\r\n]", query):
            raise ValueError("Use a short public topic query, not URLs or private identifiers")
        # Openverse returns provenance and licenses. Only approved raster CDNs survive
        # filtering; a search result cannot authorize arbitrary backend HTTP requests.
        if request.provider == "nasa":
            data = self._json(
                "https://images-api.nasa.gov/search",
                {
                    "q": query,
                    "media_type": "image",
                    "page_size": 50,
                },
            )
            rows = []
            for item in data.get("collection", {}).get("items", []):
                meta = (item.get("data") or [{}])[0]
                links = [x for x in item.get("links", []) if x.get("render") == "image"]
                if links:
                    rows.append(
                        {
                            "url": links[0]["href"],
                            "title": meta.get("title"),
                            "creator": meta.get("photographer") or meta.get("center", "NASA"),
                            "license": "NASA media usage guidelines; credit/source review required",
                            "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
                            "source_url": "https://images.nasa.gov/details/"
                            + meta.get("nasa_id", ""),
                            "description": meta.get("description", ""),
                        }
                    )
        else:
            data = self._json(
                "https://api.openverse.org/v1/images/",
                {
                    "q": query,
                    "page_size": 20,
                    "extension": "jpg,png",
                    "license_type": "commercial,modification",
                },
            )
            if not data.get("results") and len(query.split()) > 2:
                data = self._json(
                    "https://api.openverse.org/v1/images/",
                    {
                        "q": " ".join(query.split()[:2]),
                        "page_size": 20,
                        "extension": "jpg,png",
                        "license_type": "commercial,modification",
                    },
                )
            rows = [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title"),
                    "creator": r.get("creator"),
                    "license": r.get("license"),
                    "license_url": r.get("license_url"),
                    "source_url": r.get("foreign_landing_url"),
                    "description": "",
                }
                for r in data.get("results", [])
            ]
        if request.provider == "nasa":
            terms = re.findall(r"[a-z0-9]+", query.lower())

            def relevance(row):
                title = plain(row.get("title")).lower()
                description = plain(row.get("description"), 3000).lower()
                if not all(
                    re.search(r"\b" + re.escape(term) + r"\b", title + " " + description)
                    for term in terms
                ):
                    return -1
                return sum(term in title for term in terms)

            rows = sorted((r for r in rows if relevance(r) >= 0), key=relevance, reverse=True)
        results = []
        for row in rows:
            try:
                allowed_image_url(row["url"])
            except ValueError:
                continue
            if urlsplit(row["url"]).path.lower().endswith((".svg", ".gif", ".tiff", ".tif")):
                continue
            # Flickr documents a shared secret for sizes through 1024px (b).
            # Request that published size instead of stretching a 240px thumbnail.
            if urlsplit(row["url"]).hostname == "live.staticflickr.com":
                row["url"] = re.sub(
                    r"^(https://live\.staticflickr\.com/\d+/\d+_[a-f0-9]+)(?:_[smntwzcb])?\.jpg$",
                    r"\1_b.jpg",
                    row["url"],
                )
            if "filter forge" in plain(row.get("creator")).lower():
                continue
            cid = "img_" + hashlib.sha256((request.asset_id + row["url"]).encode()).hexdigest()[:20]
            record = {k: plain(v) for k, v in row.items() if k != "url"}
            record.update(candidate_id=cid, asset_id=request.asset_id, url=row["url"])
            self.candidates[cid] = record
            results.append(record)
        return results[:6]

    def download(self, asset_id, candidate_id, destination: Path):
        record = self.candidates.get(candidate_id)
        if not record or record["asset_id"] != asset_id:
            raise ValueError("Image selection must resolve to a candidate for this request")
        url = allowed_image_url(record["url"])
        # Never accept a caller/model path or follow a redirect to an arbitrary host.
        name = f"image-{hashlib.sha256(asset_id.encode()).hexdigest()[:16]}.jpg"
        destination.mkdir(parents=True, exist_ok=True)
        raw = destination / (name + ".download")
        target = destination / name
        try:
            with self.client.stream("GET", url) as response:
                response.raise_for_status()
                if response.headers.get("content-type", "").split(";")[0] not in {
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                    "application/octet-stream",
                }:
                    raise ValueError("Unsupported image response")
                size = 0
                with raw.open("wb") as output:
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_IMAGE_BYTES:
                            raise ValueError("Image exceeds byte limit")
                        output.write(chunk)
            header = raw.read_bytes()[:16]
            if not (
                header.startswith(b"\xff\xd8\xff")
                or header.startswith(b"\x89PNG\r\n\x1a\n")
                or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
            ):
                raise ValueError("Image bytes are not a supported raster")
            info = probe(raw)
            stream = next(s for s in info["streams"] if s["codec_type"] == "video")
            if not 32 <= stream["width"] <= 12000 or not 32 <= stream["height"] <= 12000:
                raise ValueError("Image dimensions outside bounds")
            if max(stream["width"], stream["height"]) < 640:
                raise ValueError("Image resolution insufficient for phone video")
            if stream["width"] * stream["height"] > 40_000_000:
                raise ValueError("Image pixel count too large")
            run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    raw,
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=1920:1920:force_original_aspect_ratio=decrease",
                    "-q:v",
                    "3",
                    target,
                ],
                timeout=45,
            )
            return {
                **record,
                "file": name,
                "sha256": sha256(target),
                "width": stream["width"],
                "height": stream["height"],
            }
        finally:
            raw.unlink(missing_ok=True)


def stage_images(brief, board, claude, work, assets, *, fixture=False):
    """Search and select outside the credential-free renderer; resume only verified files."""
    import json

    if not board.image_requests:
        return {}
    if fixture:
        # Explicit fake adapter: deterministic color fields, never external image retrieval.
        # These packs retain fixture=true and cannot pass the live publication gate.
        result = {}
        assets.mkdir(parents=True, exist_ok=True)
        for i, request in enumerate(board.image_requests):
            name = f"fixture-image-{i}.jpg"
            run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c={'0x163950' if i % 2 else '0x42305c'}:s=1080x1920",
                    "-frames:v",
                    "1",
                    assets / name,
                ]
            )
            result[request.asset_id] = {
                "file": name,
                "title": "Synthetic color-field fixture, not a subject photograph",
                "creator": "Local fake adapter",
                "license": "Synthetic fixture",
                "width": 1080,
                "height": 1920,
                "sha256": sha256(assets / name),
            }
        return result
    cache = work / "image-selection.json"
    key = digest(
        [brief.teaching_payload(), board.model_dump(), "visual-review-candidate-previews-5"]
    )
    if cache.exists():
        saved = json.loads(cache.read_text())
        if saved.get("key") == key and all(
            (assets / image["file"]).is_file() and sha256(assets / image["file"]) == image["sha256"]
            for image in saved["images"].values()
        ):
            return saved["images"]
    library = ImageLibrary()
    try:
        candidates = []
        for request in board.image_requests:
            found = library.search(request)
            if not found:
                raise ValueError(
                    f"IMAGE_REVIEW_REQUIRED: no approved images for {request.asset_id}"
                )
            candidates.extend(found)
        atomic_json(work / "image-candidates.json", candidates)
        # Let the selector see actual candidates, not just misleading stock-photo titles.
        staged_candidates = {}
        visual_candidates = []
        for candidate in candidates:
            cid = candidate["candidate_id"]
            directory = work / "candidate-previews" / cid
            directory.mkdir(parents=True, exist_ok=True)
            try:
                item = library.download(candidate["asset_id"], cid, directory)
                staged_candidates[cid] = item
                visual_candidates.append({**candidate, "_preview": str(directory / item["file"])})
            except (httpx.HTTPError, ValueError):
                continue
        candidates = visual_candidates
        images, failed = {}, set()
        approved = False
        for attempt in range(3):
            remaining = [
                c
                for c in candidates
                if c["asset_id"] not in images
                and c["candidate_id"] not in failed
                and c["url"] not in {i.get("url") for i in images.values()}
            ]
            required = {a.asset_id for a in board.image_requests} - images.keys()
            if not required:
                break
            if not required <= {c["asset_id"] for c in remaining}:
                raise ValueError("IMAGE_REVIEW_REQUIRED: no retrievable candidates remain")
            selection = claude.select_images(brief, board, remaining)
            for choice in selection.choices:
                try:
                    candidate = dict(staged_candidates[choice.candidate_id])
                    source = work / "candidate-previews" / choice.candidate_id / candidate["file"]
                    shutil.copyfile(source, assets / candidate["file"])
                    # Dedup actual normalized content, even when search returns different URLs.
                    fingerprint = visual_fingerprint(assets / candidate["file"])
                    if any(
                        candidate["sha256"] == old["sha256"]
                        or candidate["url"] == old.get("url")
                        or (int(fingerprint, 16) ^ int(old["fingerprint"], 16)).bit_count() <= 4
                        for old in images.values()
                    ):
                        raise ValueError("Repeated photograph across scene requests")
                    candidate["fingerprint"] = fingerprint
                    images[choice.asset_id] = candidate
                except (httpx.HTTPError, ValueError):
                    failed.add(choice.candidate_id)
            if len(images) == len(board.image_requests):
                review = claude.review_images(board, images, assets)
                atomic_json(work / "image-review.json", review.model_dump())
                atomic_json(work / f"image-review-{attempt}.json", review.model_dump())
                if review.passed and not review.issues:
                    for framing in getattr(review, "framing", []):
                        images[framing.asset_id].setdefault("framing", {})[framing.shot_id] = (
                            framing.model_dump()
                        )
                    approved = True
                    break
                rejected = {
                    asset_id
                    for asset_id in images
                    if any(asset_id in issue for issue in review.issues)
                }
                # If the reviewer cannot localize a problem, do not assume any image passed.
                for asset_id in rejected or set(images):
                    failed.add(images.pop(asset_id)["candidate_id"])
        if not approved:
            raise ValueError("IMAGE_REVIEW_REQUIRED: retrieval/visual review attempts exhausted")
        atomic_json(cache, {"key": key, "images": images})
        return images
    finally:
        library.client.close()


def visual_fingerprint(path):
    """64-bit difference hash; conservative near-duplicate detection on decoded pixels."""
    pixels = run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            path,
            "-vf",
            "scale=9:8,format=gray",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "pipe:1",
        ]
    ).stdout
    if len(pixels) != 72:
        raise ValueError("Invalid fingerprint frame")
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return f"{bits:016x}"
