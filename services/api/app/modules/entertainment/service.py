"""Authenticated catalog service; saved batches and Atlas share pagination rules."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft7Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .pagination import CursorCodec, CursorError, batch_revision

ROOT = Path(__file__).resolve().parents[5]
FEED_SCHEMA = json.loads((ROOT / 'contracts/schemas/entertainment/feed-page.v1.schema.json').read_text())
FEED_VALIDATOR = Draft7Validator(FEED_SCHEMA, format_checker=FormatChecker())


class CatalogFailure(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def normalized_items(items):
    """Validate and allowlist client fields; provider responses/cookies never persist."""
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError('A catalog batch must contain at most 100 records.')
    FEED_VALIDATOR.validate({'schema_version': '1', 'items': items, 'next_cursor': None})
    result, seen = [], set()
    definitions = FEED_SCHEMA['definitions']
    for item in items:
        key = item['provider'], item['provider_video_id']
        if key in seen:
            continue
        seen.add(key)
        record = {key: item[key] for key in definitions['EntertainmentVideo']['required']}
        record['creator'] = {key: item['creator'][key] for key in ('handle', 'display_name', 'attribution_url')}
        record['playback'] = {key: item['playback'][key] for key in definitions['PlaybackSource']['required']}
        for timestamp in (record['acquired_at'], record['playback']['expires_at']):
            if timestamp and datetime.fromisoformat(timestamp.replace('Z', '+00:00')).tzinfo is None:
                raise ValueError('Catalog timestamps require an explicit zone.')
        for url in (record['source_url'], record['thumbnail_url'], record['creator']['attribution_url'], record['playback']['url']):
            if url:
                parsed = urlsplit(url)
                if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                    raise ValueError('Catalog URLs must be credential-free HTTPS URLs.')
        if len(json.dumps(record).encode()) > 32768:
            raise ValueError('Catalog record exceeds metadata limits.')
        result.append(record)
    if len({item['video_id'] for item in result}) != len(result):
        raise ValueError('Catalog video IDs must be unique.')
    return result


def playable(item, now):
    expiry = item['playback']['expires_at']
    return item['availability'] == 'ready' and item['playback']['kind'] != 'embed' and (not expiry or datetime.fromisoformat(expiry.replace('Z', '+00:00')) > now)


class CatalogService:
    def __init__(self, repository, cursor_secret=None, clock=None):
        self.repository = repository
        self.cursors = CursorCodec(cursor_secret)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _items(self, user):
        return self.repository.read_items(user)

    def candidate_snapshot(self, user, limit=100):
        """One owner-scoped atomic snapshot for the unified feed, without paging reads."""
        now = self.clock()
        return [item for item in self._items(user) if playable(item, now)][:max(0, min(limit, 100))]

    def list_candidates(self, user, cursor=None, limit=5):
        if type(limit) is not int or not 1 <= limit <= 20:
            raise CatalogFailure(422, 'INVALID_LIMIT', 'Choose a page size from 1 to 20.')
        items = self._items(user)
        revision = batch_revision(items)
        try:
            offset = self.cursors.decode(cursor, user['user_id'], revision, limit) if cursor else 0
        except CursorError as error:
            raise CatalogFailure(409 if error.stale else 422, 'STALE_CURSOR' if error.stale else 'INVALID_CURSOR', 'Reload the feed to retrieve a fresh page.') from None
        # Paginate before eligibility filtering so expiry cannot shift later offsets.
        window = items[offset:offset + limit]
        end = offset + len(window)
        return {'schema_version': '1', 'items': [item for item in window if playable(item, self.clock())],
                'next_cursor': self.cursors.encode(end, user['user_id'], revision, limit) if end < len(items) else None}

    def resolve_playback(self, video_id, user):
        for item in self._items(user):
            if item['video_id'] == video_id:
                if not playable(item, self.clock()):
                    raise CatalogFailure(410, 'PLAYBACK_UNAVAILABLE', 'This clip is unavailable or expired. Skip it or retrieve a fresh catalog.')
                return item['playback']
        raise CatalogFailure(404, 'VIDEO_NOT_FOUND', 'This clip is not in your catalog.')


class SavedCatalog(CatalogService):
    """Finite local cache. Never binds automatically to the first signed-in caller."""
    def __init__(self, catalog_path: Path, owner_path: Path, **kwargs):
        self.catalog_path, self.owner_path = catalog_path, owner_path
        super().__init__(self, **kwargs)

    def read_items(self, user):
        try:
            owner = json.loads(self.owner_path.read_text())['user_id']
        except (OSError, ValueError, KeyError, TypeError):
            raise CatalogFailure(403, 'PREVIEW_NOT_BOUND', 'Your Instagram preview is not connected yet. Copy the App user ID from The lab.') from None
        if not isinstance(owner, str) or not owner or owner != user['user_id']:
            raise CatalogFailure(404, 'CATALOG_NOT_FOUND', 'No catalog is connected to this account.')
        try:
            page = json.loads(self.catalog_path.read_text())
            FEED_VALIDATOR.validate(page)
            return normalized_items(page['items'])
        except (OSError, ValueError, TypeError, KeyError, ValidationError):
            raise CatalogFailure(503, 'CATALOG_UNAVAILABLE', 'The saved catalog is unavailable. Retrieve a fresh batch locally.') from None
