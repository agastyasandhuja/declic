"""Single-attempt private comments: page, owner, connection, and payload fences."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.modules.entertainment.comments import OwnedComments, comments_page
from app.modules.entertainment.service import CatalogFailure


def comment(identifier):
    return {
        "pk": str(identifier),
        "text": "Generic comment",
        "user": {"username": "reader", "full_name": "Reader", "cookie": "must-not-leak"},
        "created_at": 1700000000,
        "comment_like_count": 3,
        "private": "must-not-leak",
    }


@pytest.fixture
def comments():
    row = {"connection_id": "connection-1", "status": "connected", "sealed": "private"}
    calls = []
    responses = [
        {
            "comments": [comment(i) for i in range(1, 26)],
            "next_max_id": "private-cursor",
            "has_more_comments": True,
        },
        {"comments": [comment(25), comment(26)], "has_more_comments": False},
    ]

    def request(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return responses.pop(0)

    provider = SimpleNamespace(_request=request, close=lambda: None)
    social = SimpleNamespace(
        get=lambda owner: deepcopy(row) if owner == "alice" else None,
        vault=SimpleNamespace(open=lambda *args: {"session": {}}),
    )
    repository = SimpleNamespace(
        read_items=lambda user: (
            [{"video_id": "instagram_123", "provider_video_id": "123", "provider": "instagram"}]
            if user["user_id"] == "alice"
            else []
        )
    )
    now = [0]
    reader = OwnedComments(
        social, repository, monotonic=lambda: now[0], provider_factory=lambda saved: provider
    )
    return SimpleNamespace(
        row=row,
        calls=calls,
        responses=responses,
        provider=provider,
        reader=reader,
        social=social,
        now=now,
    )


def test_comments_paging_retains_overflow_and_deduplicates_provider(comments):
    c = comments
    first = c.reader.read("alice", "instagram_123")
    assert len(first["items"]) == 20 and first["next_cursor"]
    assert "private" not in str(first) and "must-not-leak" not in str(first)
    assert c.reader.read("alice", "instagram_123") == first and len(c.calls) == 1
    second = c.reader.read("alice", "instagram_123", first["next_cursor"])
    assert len(second["items"]) == 5 and len(c.calls) == 1
    third = c.reader.read("alice", "instagram_123", second["next_cursor"])
    assert [item["comment_id"] for item in third["items"]] == ["26"]
    assert third["next_cursor"] is None and len(c.calls) == 2
    assert c.calls[1][1]["params"]["max_id"] == "private-cursor"


def test_unknown_owner_clip_and_changed_connection_never_reuse_cache(comments):
    c = comments
    first = c.reader.read("alice", "instagram_123")
    assert c.reader.read("bob", "instagram_123")["availability"] == "unavailable"
    with pytest.raises(CatalogFailure):
        c.reader.read("alice", "instagram_999")
    c.row["connection_id"] = "replacement"
    with pytest.raises(CatalogFailure) as error:
        c.reader.read("alice", "instagram_123", first["next_cursor"])
    assert error.value.code == "STALE_CURSOR" and len(c.calls) == 1
    c.row["status"] = "disconnected"
    assert c.reader.read("alice", "instagram_123")["items"] == []


def test_inflight_disconnect_drops_payload(comments):
    c = comments

    def read(*args, **kwargs):
        c.row["status"] = "disconnected"
        return {"comments": [comment(1)]}

    c.provider._request = read
    assert c.reader.read("alice", "instagram_123")["items"] == []


def test_rate_limit_is_honored_without_repeating_provider_request(comments):
    c = comments

    def read(*args, **kwargs):
        c.calls.append("read")
        error = CatalogFailure(503, "INSTAGRAM_RATE_LIMITED", "Wait")
        error.retry_after = 300
        raise error

    c.provider._request = read
    for _ in range(2):
        with pytest.raises(CatalogFailure):
            c.reader.read("alice", "instagram_123")
    assert len(c.calls) == 1


def test_provider_page_errors_are_bounded_and_empty_disabled_is_honest():
    for response in (
        {"comments": [comment(i) for i in range(101)]},
        {"comments": "invalid"},
        {"comments": [], "next_max_id": "x" * 4097},
    ):
        provider = SimpleNamespace(_request=lambda *args, response=response, **kwargs: response)
        with pytest.raises(CatalogFailure):
            comments_page(provider, "123", None, 20)
    provider = SimpleNamespace(
        _request=lambda *args, **kwargs: {"comments": [], "comments_disabled": True}
    )
    assert comments_page(provider, "123", None, 20) == ([], None, "comments_disabled")


def test_cursor_bound_to_limit_and_expires(comments):
    first = comments.reader.read("alice", "instagram_123")
    with pytest.raises(CatalogFailure):
        comments.reader.read("alice", "instagram_123", first["next_cursor"], 10)
    comments.now[0] = 301
    with pytest.raises(CatalogFailure):
        comments.reader.read("alice", "instagram_123", first["next_cursor"])


def test_long_or_repeated_reel_cursor_preserves_valid_page_and_ends_stream():
    from app.modules.entertainment.instagram import InstagramReelsProvider

    provider = InstagramReelsProvider(SimpleNamespace())
    provider._normalize = lambda rows: [{"valid": True}] if rows else []
    for continuation in ("x" * 4116, "previous"):
        provider._request = lambda *args, continuation=continuation, **kwargs: {
            "items": [{"media": {"pk": "123"}}],
            "paging_info": {"max_id": continuation, "more_available": True},
        }
        page = provider.read_page("previous")
        assert page.items == [{"valid": True}] and page.next_cursor is None
