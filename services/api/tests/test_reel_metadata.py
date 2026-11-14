from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from jsonschema.exceptions import ValidationError

from app.core.integration import FeedEntertainmentReader
from app.modules.entertainment.instagram import normalize_reel
from app.modules.entertainment.service import normalized_items


def media(**extra):
    return SimpleNamespace(
        media_type=2,
        product_type="clips",
        pk="123",
        code="synthetic",
        user=SimpleNamespace(username="synthetic"),
        video_url="https://video.cdninstagram.com/123.mp4",
        caption_text="Synthetic clip",
        video_duration=15,
        **extra,
    )


def test_provider_counts_and_thumbnail_survive_catalog_and_feed_projection():
    item = normalize_reel(
        media(
            like_count=33000,
            comment_count=241,
            thumbnail_url="https://image.cdninstagram.com/123.jpg",
        ),
        datetime.now(UTC),
    )
    catalog = SimpleNamespace(candidate_snapshot=lambda user, limit: normalized_items([item]))
    candidate = FeedEntertainmentReader(catalog).list_candidates("test_user", 10)[0]
    assert candidate.like_count == 33000
    assert candidate.comment_count == 241
    assert str(candidate.thumbnail_url) == "https://image.cdninstagram.com/123.jpg"


@pytest.mark.parametrize("count", [None, -1, True, "33000", 3.3, 9007199254740992])
def test_hidden_or_invalid_counts_are_unknown(count):
    item = normalize_reel(media(like_count=count, comment_count=count), datetime.now(UTC))
    assert item["like_count"] is None
    assert item["comment_count"] is None


@pytest.mark.parametrize(
    "url",
    [
        "http://image.cdninstagram.com/a.jpg",
        "https://cdninstagram.com.evil.example/a.jpg",
        "https://user:pass@image.cdninstagram.com/a.jpg",
        "https://image.cdninstagram.com:evil/a.jpg",
        "https://image.cdninstagram.com/a.jpg#fragment",
    ],
)
def test_unsafe_thumbnail_does_not_discard_valid_reel(url):
    item = normalize_reel(media(thumbnail_url=url), datetime.now(UTC))
    assert item["thumbnail_url"] is None
    assert item["video_id"] == "instagram_123"


def test_old_records_remain_valid_but_invalid_wire_counts_are_rejected():
    item = normalize_reel(media(), datetime.now(UTC))
    item.pop("like_count")
    item.pop("comment_count")
    assert normalized_items([item])[0] == item
    for invalid in (-1, True, "33000", 9007199254740992):
        with pytest.raises(ValidationError):
            normalized_items([{**item, "like_count": invalid}])
