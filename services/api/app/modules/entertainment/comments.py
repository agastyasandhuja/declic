"""Bounded read-only comments for known Reels on the owner's current connection."""

import re
import secrets
import threading
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import UTC, datetime

from .instagram import InstagramReelsProvider, make_instagram_client
from .service import CatalogFailure


def comments_page(provider, provider_video_id, cursor, limit):
    if not re.fullmatch(r"\d{1,32}", provider_video_id):
        raise CatalogFailure(404, "VIDEO_NOT_FOUND", "Comments are unavailable for this clip.")
    # The pinned SDK's comments_chunk loops through pages using private_request;
    # use its documented endpoint through our single-attempt transport instead.
    params = {"can_support_threading": "true", "permalink_enabled": "false", "count": str(limit)}
    if cursor:
        params["max_id"] = cursor
    response = provider._request(f"media/{provider_video_id}/comments/", params=params)
    if not isinstance(response, dict) or not isinstance(response.get("comments", []), list):
        raise CatalogFailure(503, "INSTAGRAM_INVALID_RESPONSE", "Comments could not be read.")
    rows = response.get("comments", [])
    if len(rows) > 100:
        raise CatalogFailure(503, "INSTAGRAM_INVALID_RESPONSE", "Comments exceeded the page limit.")
    if response.get("comments_disabled") is True:
        return [], None, "comments_disabled"
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        author = row.get("user")
        if not isinstance(author, dict):
            continue
        identifier, username, text = str(row.get("pk", "")), author.get("username"), row.get("text")
        if (
            not re.fullmatch(r"\d{1,32}", identifier)
            or identifier in seen
            or not isinstance(username, str)
            or not re.fullmatch(r"[A-Za-z0-9_.]{1,30}", username)
            or not isinstance(text, str)
        ):
            continue
        likes = row.get("comment_like_count", 0)
        created = row.get("created_at_utc", row.get("created_at"))
        try:
            timestamp = (
                datetime.fromtimestamp(created, UTC).isoformat()
                if type(created) in (int, float) and 0 <= created <= time.time() + 300
                else None
            )
        except (ValueError, OverflowError, OSError):
            timestamp = None
        result.append(
            {
                "comment_id": identifier,
                "text": text[:4000],
                "author": {
                    "username": username,
                    "display_name": (author.get("full_name") or "")[:200]
                    if isinstance(author.get("full_name", ""), str)
                    else "",
                },
                "like_count": max(0, min(likes, 1_000_000_000)) if type(likes) is int else 0,
                "created_at": timestamp,
            }
        )
        seen.add(identifier)
    continuation = response.get("next_max_id") or response.get("max_id") or None
    if continuation is not None and (not isinstance(continuation, str) or len(continuation) > 4096):
        raise CatalogFailure(503, "INSTAGRAM_INVALID_RESPONSE", "Comments could not be read.")
    if response.get("has_more_comments") is False or continuation == cursor:
        continuation = None
    return result, continuation, None


class OwnedComments:
    def __init__(self, social, repository, *, monotonic=time.monotonic, provider_factory=None):
        self.social, self.repository = social, repository
        self.clock = monotonic
        self.provider_factory = provider_factory or (
            lambda saved: InstagramReelsProvider(make_instagram_client(saved["session"]))
        )
        self.lock = threading.RLock()
        self.pages, self.cursors, self.busy, self.cooldowns = (
            OrderedDict(),
            OrderedDict(),
            set(),
            OrderedDict(),
        )

    def _bounded(self, mapping, key, value):
        mapping[key] = value
        mapping.move_to_end(key)
        while len(mapping) > 128:
            mapping.popitem(last=False)

    def _identity(self, owner, video_id):
        row = self.social.get(owner)
        if not row or row.get("status") != "connected" or not row.get("sealed"):
            return None, None
        items = self.repository.read_items({"user_id": owner})
        item = next((item for item in items if item["video_id"] == video_id), None)
        if not item or item["provider"] != "instagram":
            raise CatalogFailure(404, "VIDEO_NOT_FOUND", "Comments are unavailable for this clip.")
        return row, item

    def read(self, owner, video_id, cursor=None, limit=20):
        if type(limit) is not int or not 1 <= limit <= 20:
            raise CatalogFailure(422, "INVALID_LIMIT", "Choose 1–20 comments.")
        row, item = self._identity(owner, video_id)
        unavailable = {
            "schema_version": "1",
            "items": [],
            "next_cursor": None,
            "availability": "unavailable",
            "reason": "instagram_not_connected",
        }
        if row is None:
            return unavailable
        identity = (owner, row["connection_id"], video_id, limit)
        key = (*identity, cursor)
        now = self.clock()
        with self.lock:
            cached = self.pages.get(key)
            if cached and cached[0] > now:
                return deepcopy(cached[1])
            continuation, pending, seen_ids, hops = None, [], [], 0
            if cursor:
                state = self.cursors.get(cursor)
                if not state or state["identity"] != identity or state["expires"] <= now:
                    raise CatalogFailure(409, "STALE_CURSOR", "Reload comments for this clip.")
                continuation, pending, seen_ids, hops = (
                    state["upstream"],
                    state["pending"],
                    state["seen"],
                    state["hops"],
                )
            if identity in self.busy or len(self.busy) >= 32:
                raise CatalogFailure(503, "INSTAGRAM_BUSY", "Comments are loading. Retry shortly.")
            cooldown = self.cooldowns.get((owner, row["connection_id"]), 0)
            if not pending and (row.get("retry_after", 0) > time.time() or cooldown > now):
                raise CatalogFailure(
                    503, "INSTAGRAM_RATE_LIMITED", "Instagram is cooling down. Retry shortly."
                )
            self.busy.add(identity)
        try:
            reason = None
            if not pending:
                if hops >= 5:
                    return {**unavailable, "availability": "available", "reason": "page_limit"}
                saved = self.social.vault.open(owner, "instagram", row["sealed"])
                provider = self.provider_factory(saved)
                try:
                    pending, next_upstream, reason = comments_page(
                        provider, item["provider_video_id"], continuation, limit
                    )
                    if next_upstream == continuation:
                        next_upstream = None
                    continuation = next_upstream
                    hops += 1
                except CatalogFailure as error:
                    with self.lock:
                        self._bounded(
                            self.cooldowns,
                            (owner, row["connection_id"]),
                            self.clock() + getattr(error, "retry_after", 30),
                        )
                    raise
                finally:
                    provider.close()
            # Recheck the connection after the network read; no old account data
            # may publish after disconnect/replacement, even to the same app owner.
            current = self.social.get(owner)
            if (
                not current
                or current.get("status") != "connected"
                or current.get("connection_id") != row["connection_id"]
            ):
                return unavailable
            pending = [comment for comment in pending if comment["comment_id"] not in seen_ids]
            items, remaining = pending[:limit], pending[limit:]
            seen_ids = [*seen_ids, *(comment["comment_id"] for comment in items)][-500:]
            result = {
                "schema_version": "1",
                "items": items,
                "next_cursor": None,
                "availability": "unavailable" if reason else "available",
            }
            if reason:
                result["reason"] = reason
            with self.lock:
                if remaining or (continuation and hops < 5):
                    token = secrets.token_urlsafe(32)
                    self._bounded(
                        self.cursors,
                        token,
                        {
                            "identity": identity,
                            "expires": self.clock() + 300,
                            "upstream": continuation,
                            "pending": remaining,
                            "seen": seen_ids,
                            "hops": hops,
                        },
                    )
                    result["next_cursor"] = token
                self._bounded(self.pages, key, (self.clock() + 60, deepcopy(result)))
            return result
        finally:
            with self.lock:
                self.busy.discard(identity)
