"""Owner-bound, bounded live feed. No provider state is sent to the mobile client."""
from collections import OrderedDict, deque
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import math
import secrets
from threading import Lock
import time
from uuid import UUID
from jsonschema.exceptions import ValidationError

from .pagination import CursorCodec, CursorError
from .service import CatalogFailure, normalized_items, playable


class LiveInstagramCatalog:
    """One demo connection/process; core supplies identity and owns shared assembly.

    At most 100 pending + 100 recently issued metadata records, 20 cached page
    references, 2048 seen IDs and 128 provider-cursor hashes are held in memory.
    Old cursor replay fails explicitly; active scrolling can continue past 100.
    """
    def __init__(self, owner_user_id, provider, *, cursor_secret=None, clock=None,
                 monotonic=None, minimum_interval=2, session_seconds=1800, diagnostics=None):
        self.owner = str(UUID(owner_user_id))
        self.provider, self.cursors = provider, CursorCodec(cursor_secret)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.monotonic = monotonic or time.monotonic
        self.minimum_interval, self.session_seconds = minimum_interval, session_seconds
        self.lock = Lock()
        self.records, self.pages, self.refresh_at = OrderedDict(), OrderedDict(), OrderedDict()
        self.seen, self.seen_order = set(), deque()
        self.pending, self.provider_cursors = deque(), deque(maxlen=128)
        self.reconnect, self.cooldown_until, self.failure = False, 0, None
        self.epoch, self.started, self.root_at = None, 0, float('-inf')
        self.provider_cursor, self.exhausted, self.next_page = None, False, 0
        self.next_fetch_at = 0
        self.diagnostics = diagnostics
        self.metrics = {'provider_reads': 0, 'provider_items': 0, 'new_items': 0,
                        'duplicates': 0, 'empty_windows': 0, 'pacing_deferrals': 0,
                        'last_error': None, 'end_reason': None}

    def _diagnose(self):
        if self.diagnostics is None:
            return
        try:
            value = {'schema_version': '1', 'checked_at': self.clock().isoformat(),
                     **self.metrics, 'exhausted': self.exhausted,
                     'pending_items': len(self.pending), 'recent_items': len(self.records),
                     'cached_pages': len(self.pages),
                     'cooldown_seconds': max(0, math.ceil(self.cooldown_until - self.monotonic())),
                     'reconnect_required': self.reconnect}
            self.diagnostics(value)
        except Exception:
            pass  # Local diagnostic persistence must not break playback.

    def _authorize(self, user):
        if user.get('user_id') != self.owner:
            raise CatalogFailure(404, 'CATALOG_NOT_FOUND', 'No Instagram connection belongs to this app account.')

    def _unavailable(self):
        if self.reconnect:
            raise self.failure
        if self.monotonic() < self.cooldown_until:
            failure = CatalogFailure(self.failure.status, self.failure.code, self.failure.message)
            failure.retry_after = max(1, math.ceil(self.cooldown_until - self.monotonic()))
            raise failure

    def _provider_call(self, call):
        self._unavailable()
        now = self.monotonic()
        if now < self.next_fetch_at:
            self.metrics['pacing_deferrals'] += 1
            self.metrics['last_error'] = 'INSTAGRAM_BUSY'
            failure = CatalogFailure(503, 'INSTAGRAM_BUSY', 'More Reels are warming up. Keep watching and retry shortly.')
            failure.retry_after = max(1, math.ceil(self.next_fetch_at - now))
            raise failure
        self.next_fetch_at = now + self.minimum_interval
        self.metrics['provider_reads'] += 1
        try:
            result = call()
            self.metrics['last_error'] = None
            return result
        except CatalogFailure as failure:
            self.metrics['last_error'] = failure.code if failure.code in {
                'INSTAGRAM_RECONNECT_REQUIRED', 'INSTAGRAM_RATE_LIMITED',
                'INSTAGRAM_UNAVAILABLE', 'INSTAGRAM_INVALID_RESPONSE', 'PLAYBACK_UNAVAILABLE'} else 'DEPENDENCY_FAILED'
            if failure.code == 'INSTAGRAM_RECONNECT_REQUIRED':
                self.reconnect, self.failure = True, failure
            elif failure.status >= 500:
                failure.retry_after = getattr(failure, 'retry_after', 30)
                self.cooldown_until = self.monotonic() + failure.retry_after
                self.failure = failure
            raise

    def _remember(self, item):
        self.records[item['video_id']] = item
        self.records.move_to_end(item['video_id'])
        while len(self.records) > 100:
            self.records.popitem(last=False)

    def _cached_page(self, number):
        ids, cursor = self.pages[number]
        if any(identifier not in self.records for identifier in ids):
            raise CatalogFailure(409, 'STALE_CURSOR', 'This feed page has expired. Reload for fresh Reels.')
        return {'schema_version': '1', 'items': [deepcopy(self.records[identifier]) for identifier in ids
                 if playable(self.records[identifier], self.clock())], 'next_cursor': cursor}

    def list_candidates(self, user, cursor=None, limit=5):
        self._authorize(user)
        if type(limit) is not int or not 1 <= limit <= 20:
            raise CatalogFailure(422, 'INVALID_LIMIT', 'Choose a page size from 1 to 20.')
        if not self.lock.acquire(timeout=0.05):
            raise CatalogFailure(503, 'INSTAGRAM_BUSY', 'Another page is loading. Retry shortly.')
        try:
            now = self.monotonic()
            if cursor:
                try:
                    number = self.cursors.decode(cursor, self.owner, self.epoch, limit)
                except CursorError as error:
                    raise CatalogFailure(409 if error.stale else 422,
                        'STALE_CURSOR' if error.stale else 'INVALID_CURSOR', 'Reload the feed for a current page.') from None
                if now - self.started >= self.session_seconds:
                    raise CatalogFailure(409, 'STALE_CURSOR', 'This feed session has expired. Reload for fresh Reels.')
            else:
                # GET retries reuse a root for 30s, avoiding duplicate provider reads.
                if self.epoch is not None and 0 in self.pages and now - self.root_at < 30 and limit == self.page_size:
                    return self._cached_page(0)
                self._unavailable()
                self.epoch, self.started, self.root_at = secrets.token_hex(16), now, now
                self.page_size, self.next_page = limit, 0
                self.provider_cursor, self.exhausted = None, False
                self.metrics['end_reason'] = None
                self.pending.clear(); self.pages.clear(); self.provider_cursors.clear()
                number = 0
            if number in self.pages:
                return self._cached_page(number)
            if number != self.next_page:
                raise CatalogFailure(409, 'STALE_CURSOR', 'This feed page is no longer cached. Reload for fresh Reels.')
            if not self.pending and not self.exhausted:
                page = self._provider_call(lambda: self.provider.read_page(self.provider_cursor))
                try:
                    items = normalized_items(page.items)
                except (ValueError, TypeError, KeyError, ValidationError):
                    raise CatalogFailure(503, 'INSTAGRAM_INVALID_RESPONSE', 'Instagram returned unreadable clip metadata.') from None
                next_cursor = page.next_cursor
                if next_cursor is not None and (not isinstance(next_cursor, str) or len(next_cursor) > 4096):
                    raise CatalogFailure(503, 'INSTAGRAM_INVALID_RESPONSE', 'Instagram returned an unreadable page.')
                fingerprint = hashlib.sha256(next_cursor.encode()).digest() if next_cursor else None
                if not next_cursor or fingerprint in self.provider_cursors:
                    self.exhausted = True
                    self.metrics['end_reason'] = 'provider_end' if not next_cursor else 'repeated_cursor'
                else:
                    self.provider_cursors.append(fingerprint)
                self.provider_cursor = next_cursor
                self.metrics['provider_items'] += len(items)
                added = 0
                for item in items:
                    identifier = item['provider_video_id']
                    if identifier in self.seen:
                        self.metrics['duplicates'] += 1
                        continue
                    if not playable(item, self.clock()):
                        continue
                    self.seen.add(identifier); self.seen_order.append(identifier)
                    while len(self.seen_order) > 2048:
                        self.seen.remove(self.seen_order.popleft())
                    self.pending.append(item)
                    added += 1
                self.metrics['new_items'] += added
                if not added:
                    self.metrics['empty_windows'] += 1
            items = []
            while self.pending and len(items) < limit:
                item = self.pending.popleft()
                if playable(item, self.clock()):
                    items.append(item)
            for item in items:
                self._remember(item)
            token = self.cursors.encode(number + 1, self.owner, self.epoch, limit) if self.pending or not self.exhausted else None
            self.pages[number] = ([item['video_id'] for item in items], token)
            while len(self.pages) > 20:
                self.pages.popitem(last=False)
            self.next_page = number + 1
            return {'schema_version': '1', 'items': deepcopy(items), 'next_cursor': token}
        finally:
            self._diagnose()
            self.lock.release()

    def resolve_playback(self, video_id, user):
        self._authorize(user)
        if not self.lock.acquire(timeout=0.05):
            raise CatalogFailure(503, 'INSTAGRAM_BUSY', 'A page is loading. Retry this clip shortly.')
        try:
            item = self.records.get(video_id)
            if item is None:
                raise CatalogFailure(404, 'VIDEO_NOT_FOUND', 'This clip is not in your recent feed.')
            if self.monotonic() - self.refresh_at.get(video_id, float('-inf')) < 30 and playable(item, self.clock()):
                return deepcopy(item['playback'])
            fresh = self._provider_call(lambda: self.provider.refresh(item['provider_video_id']))
            fresh = normalized_items([fresh])[0]
            if fresh['video_id'] != video_id or fresh['provider_video_id'] != item['provider_video_id'] or not playable(fresh, self.clock()):
                raise CatalogFailure(410, 'PLAYBACK_UNAVAILABLE', 'This Instagram clip is unavailable. Skip it.')
            self._remember(fresh)
            self.refresh_at[video_id] = self.monotonic()
            while len(self.refresh_at) > 100:
                self.refresh_at.popitem(last=False)
            return deepcopy(fresh['playback'])
        finally:
            self._diagnose()
            self.lock.release()

    def close(self):
        self.provider.close()
