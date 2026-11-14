import httpx
import pytest

from app.modules.videos.images import ImageLibrary, allowed_image_url, stage_images
from app.modules.videos.models import ImageRequest


def request():
    return ImageRequest(
        asset_id="test", query="leatherback", purpose="Show subject", fact_ids=["size"]
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://upload.wikimedia.org/image.jpg",
        "https://127.0.0.1/x",
        "https://upload.wikimedia.org.evil.test/x",
        "https://user@upload.wikimedia.org/x",
        "https://images-assets.nasa.gov:8080/x",
        "file:///etc/passwd",
    ],
)
def test_image_urls_cannot_authorize_arbitrary_fetches(url):
    with pytest.raises(ValueError):
        allowed_image_url(url)


def test_search_filters_unapproved_hosts_and_keeps_credits():
    results = [
        {
            "url": "https://upload.wikimedia.org/a.jpg",
            "title": "<b>Leatherback</b>",
            "creator": "Author",
            "license": "by-sa",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        },
        {"url": "https://private.test/secret.jpg"},
        {"url": "https://upload.wikimedia.org/a.svg"},
    ]
    lib = ImageLibrary(
        httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"results": results}))
        )
    )
    matches = lib.search(request())
    assert len(matches) == 1
    assert matches[0]["title"] == "Leatherback" and matches[0]["creator"] == "Author"
    assert matches[0]["license"] == "by-sa"
    other = request().model_copy(update={"asset_id": "other"})
    # The same photo can be proposed for two shots without overwriting request ownership.
    assert lib.search(other)[0]["candidate_id"] != matches[0]["candidate_id"]


def candidate(lib):
    lib.candidates["selected"] = {"asset_id": "test", "url": "https://images-assets.nasa.gov/a.jpg"}


def test_selection_must_belong_to_asset(tmp_path):
    lib = ImageLibrary()
    candidate(lib)
    with pytest.raises(ValueError, match="candidate"):
        lib.download("other", "selected", tmp_path)
    lib.client.close()


@pytest.mark.parametrize(
    "status,headers,body",
    [
        (302, {"location": "http://169.254.169.254/"}, b""),
        (200, {"content-type": "image/jpeg"}, b"<svg>evil</svg>"),
        (200, {"content-type": "text/html"}, b"bad"),
        (200, {"content-type": "image/jpeg"}, b"\xff\xd8\xff" + b"x" * 12_000_001),
    ],
)
def test_reject_redirects_fake_images_and_oversized_payloads(tmp_path, status, headers, body):
    calls = []

    def respond(req):
        calls.append(str(req.url))
        return httpx.Response(status, headers=headers, content=body)

    lib = ImageLibrary(httpx.Client(transport=httpx.MockTransport(respond)))
    candidate(lib)
    with pytest.raises((httpx.HTTPError, ValueError)):
        lib.download("test", "selected", tmp_path)
    assert len(calls) == 1
    assert not list(tmp_path.iterdir())


def test_pipeline_missing_images_never_becomes_renderable(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app.modules.videos import images

    class FakeLibrary:
        client = SimpleNamespace(close=lambda: None)

        def search(self, req):
            return []

    monkeypatch.setattr(images, "ImageLibrary", FakeLibrary)
    monkeypatch.setattr(images, "visual_fingerprint", lambda path: "000000000000abcd")
    brief = SimpleNamespace(teaching_payload=lambda: {})
    board = SimpleNamespace(image_requests=[request()], model_dump=lambda: {})
    with pytest.raises(ValueError, match="IMAGE_REVIEW_REQUIRED"):
        stage_images(brief, board, None, tmp_path, tmp_path)
    assert not (tmp_path / "image-selection.json").exists()


def test_visual_rejection_selects_an_alternative_and_caches_only_approval(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app.modules.videos import images
    from app.modules.videos.media import sha256
    from app.modules.videos.models import ContentReview, ImageChoice, ImageSelection

    closed = []

    class FakeLibrary:
        client = SimpleNamespace(close=lambda: closed.append(True))

        def search(self, req):
            return [
                {"candidate_id": cid, "asset_id": "test", "url": "https://example.test/" + cid}
                for cid in ("bad", "good")
            ]

        def download(self, asset_id, candidate_id, assets):
            target = assets / "image.jpg"
            target.write_bytes(candidate_id.encode())
            return {
                "file": "image.jpg",
                "candidate_id": candidate_id,
                "sha256": sha256(target),
                "url": "https://example.test/" + candidate_id,
            }

    class FakeClaude:
        selections = []

        def select_images(self, brief, board, candidates):
            self.selections.append([c["candidate_id"] for c in candidates])
            return ImageSelection(
                choices=[ImageChoice(asset_id="test", candidate_id=candidates[0]["candidate_id"])]
            )

        def review_images(self, board, chosen, assets):
            good = chosen["test"]["candidate_id"] == "good"
            return ContentReview(
                passed=good, issues=[] if good else ["test: museum model, not living animal"]
            )

    monkeypatch.setattr(images, "ImageLibrary", FakeLibrary)
    monkeypatch.setattr(images, "visual_fingerprint", lambda path: "000000000000abcd")
    brief = SimpleNamespace(teaching_payload=lambda: {})
    board = SimpleNamespace(image_requests=[request()], model_dump=lambda: {})
    claude = FakeClaude()
    selected = stage_images(brief, board, claude, tmp_path, tmp_path)
    assert selected["test"]["candidate_id"] == "good"
    assert claude.selections == [["bad", "good"], ["good"]]
    assert closed == [True]
    assert stage_images(brief, board, claude, tmp_path, tmp_path) == selected
    assert len(claude.selections) == 2


def test_visual_review_supplies_real_shot_ids_and_image_blocks(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app.modules.videos.generation.providers import Claude
    from app.modules.videos.models import Segment, Shot

    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-key")
    (tmp_path / "image.jpg").write_bytes(b"synthetic-test-image")
    shot = Shot(
        shot_id="actual_shot",
        segment_id="spoken",
        kind="image",
        asset_ids=["test"],
        fact_ids=["size"],
    )
    segment = Segment(
        segment_id="spoken",
        speaker_role="narrator",
        spoken_text="A leatherback turtle",
        fact_ids=["size"],
    )
    board = SimpleNamespace(image_requests=[request()], shots=[shot], segments=[segment])

    def respond(req):
        import json

        content = json.loads(req.content)["messages"][0]["content"]
        payload = json.loads(content[0]["text"])
        assert payload["shots"][0]["shot_id"] == "actual_shot"
        assert payload["narration"][0]["segment_id"] == "spoken"
        assert payload["required_framing_pairs"] == [["actual_shot", "test"]]
        assert any(block["type"] == "image" for block in content)
        result = {
            "passed": True,
            "issues": [],
            "framing": [
                {
                    "shot_id": "actual_shot",
                    "asset_id": "test",
                    "focus_x": 0.2,
                    "focus_y": 0.5,
                    "fit": "contain",
                    "zoom_start": 1,
                    "zoom_end": 1.1,
                }
            ],
        }
        return httpx.Response(
            200,
            json={
                "content": [{"type": "tool_use", "name": "submit_stage_result", "input": result}]
            },
        )

    provider = Claude(client=httpx.Client(transport=httpx.MockTransport(respond)))
    review = provider.review_images(board, {"test": {"file": "image.jpg"}}, tmp_path)
    assert review.framing[0].focus_x == 0.2


def test_flickr_search_promotes_thumbnail_without_corrupting_large_url(monkeypatch):
    library = ImageLibrary()
    monkeypatch.setattr(
        library,
        "_json",
        lambda *args: {
            "results": [
                {"url": "https://live.staticflickr.com/1234/6757831463_0103c636e7_b.jpg"},
                {"url": "https://live.staticflickr.com/1234/6757831464_0103c636e7_m.jpg"},
            ]
        },
    )
    results = library.search(request())
    assert [r["url"] for r in results] == [
        "https://live.staticflickr.com/1234/6757831463_0103c636e7_b.jpg",
        "https://live.staticflickr.com/1234/6757831464_0103c636e7_b.jpg",
    ]
    library.client.close()


def test_content_duplicate_rejected_even_under_different_urls(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app.modules.videos import images
    from app.modules.videos.models import ImageChoice, ImageSelection

    class FakeLibrary:
        client = SimpleNamespace(close=lambda: None)

        def search(self, req):
            return [
                {
                    "candidate_id": req.asset_id,
                    "asset_id": req.asset_id,
                    "url": "https://example.test/" + req.asset_id,
                }
            ]

        def download(self, asset_id, candidate_id, assets):
            (assets / f"{asset_id}.jpg").write_bytes(b"identical-photo")
            return {
                "file": f"{asset_id}.jpg",
                "sha256": "same-digest",
                "candidate_id": candidate_id,
                "url": "https://example.test/" + asset_id,
            }

    class FakeClaude:
        def select_images(self, brief, board, candidates):
            return ImageSelection(
                choices=[
                    ImageChoice(asset_id=c["asset_id"], candidate_id=c["candidate_id"])
                    for c in candidates
                ]
            )

        def review_images(self, *args):
            pytest.fail("Duplicate set must be rejected before visual approval")

    monkeypatch.setattr(images, "ImageLibrary", FakeLibrary)
    monkeypatch.setattr(images, "visual_fingerprint", lambda path: "1234567812345678")
    board = SimpleNamespace(
        image_requests=[request().model_copy(update={"asset_id": i}) for i in ("one", "two")],
        model_dump=lambda: {},
    )
    with pytest.raises(ValueError, match="no retrievable"):
        stage_images(
            SimpleNamespace(teaching_payload=lambda: {}), board, FakeClaude(), tmp_path, tmp_path
        )
