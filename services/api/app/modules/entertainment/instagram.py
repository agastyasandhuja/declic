"""Single-attempt Instagram reads. Credentials and provider cursors stay server-side."""
from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
import logging
import math
import os
import re
from urllib.parse import urlsplit
from threading import RLock

from .service import CatalogFailure, normalized_items


@dataclass(frozen=True)
class ProviderPage:
    items: list[dict]
    next_cursor: str | None


_quiet_lock = RLock()


@contextlib.contextmanager
def quiet_instagram():
    # The pinned SDK prints provider payloads. Serialize process-global capture
    # so concurrent login/refresh calls cannot restore a closed stream.
    with _quiet_lock:
        previous = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        try:
            with open(os.devnull, 'w') as sink:
                with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    yield
        finally:
            logging.disable(previous)


def make_instagram_client(settings=None):
    if version('instagrapi') != '3.2.12':
        raise ValueError('Use the pinned instagrapi 3.2.12 environment.')
    from instagrapi import Client

    with quiet_instagram():
        effective = {**(settings or {}), 'session_retry_total': 0,
                     'public_request_retries_count': 1, 'request_timeout': 0.2,
                     'tls_verify': True}
        client = Client(settings=effective)
        client.with_challenge_flow = False
        def stop(_client, error):
            raise error
        client.handle_exception = stop
        for session in (client.private, client.public):
            original = session.request
            def bounded(*args, _request=original, **kwargs):
                kwargs.update(timeout=(3, 7), allow_redirects=False, verify=True)
                return _request(*args, **kwargs)
            session.request = bounded
    return client


def provider_failure(error):
    # Inspect only a fixed class-name allowlist; never emit exception text/payloads.
    kind = type(error).__name__
    if kind in {'LoginRequired', 'ChallengeRequired', 'TwoFactorRequired', 'BadPassword',
                'AccountSuspended', 'ClientUnauthorizedError', 'ClientForbiddenError',
                'ClientNeedsUpgradeError', 'FeedbackRequired', 'SentryBlock'}:
        return CatalogFailure(409, 'INSTAGRAM_RECONNECT_REQUIRED',
                              'Instagram needs attention. Review Instagram on your phone, then reconnect locally.')
    if kind in {'RateLimitError', 'PleaseWaitFewMinutes', 'ClientThrottledError'}:
        failure = CatalogFailure(503, 'INSTAGRAM_RATE_LIMITED',
                                 'Instagram is limiting requests. Keep watching loaded clips and retry in five minutes.')
        failure.retry_after = 300
        return failure
    if kind in {'MediaUnavailable', 'MediaNotFound', 'ClientNotFoundError'}:
        return CatalogFailure(410, 'PLAYBACK_UNAVAILABLE', 'This Instagram clip is no longer available. Skip it.')
    return CatalogFailure(503, 'INSTAGRAM_UNAVAILABLE',
                          'Instagram is temporarily unavailable. Keep watching loaded clips and retry shortly.')


def _engagement_count(value):
    # Hidden/unreported counts are unknown, never a fabricated zero.
    return value if type(value) is int and 0 <= value <= 9007199254740991 else None


def _thumbnail(value):
    if not value:
        return None
    try:
        url = str(value)
        parsed = urlsplit(url)
        if (parsed.scheme == 'https' and parsed.hostname
                and parsed.hostname.endswith(('.cdninstagram.com', '.fbcdn.net'))
                and not parsed.username and not parsed.password and not parsed.fragment
                and parsed.port in (None, 443)):
            return url
    except ValueError:
        pass
    return None


def normalize_reel(media, now):
    """Allowlist a directly playable Reel; signed URLs get a conservative freshness lease."""
    if media.media_type != 2 or media.product_type != 'clips':
        return None
    identifier, code, handle = str(media.pk), str(media.code), str(media.user.username)
    if not re.fullmatch(r'\d{1,32}', identifier) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', code) or not re.fullmatch(r'[A-Za-z0-9_.]{1,30}', handle):
        return None
    url = str(media.video_url) if media.video_url else ''
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname
            or not parsed.hostname.endswith(('.cdninstagram.com', '.fbcdn.net'))
            or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443)):
        return None
    duration = media.video_duration
    if duration is not None and (not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0):
        return None
    return normalized_items([{
        'schema_version': '1', 'video_id': f'instagram_{identifier}', 'provider': 'instagram',
        'provider_video_id': identifier, 'source_url': f'https://www.instagram.com/reel/{code}/',
        'creator': {'handle': handle, 'display_name': f'@{handle}', 'attribution_url': f'https://www.instagram.com/{handle}/'},
        'caption': (media.caption_text or '')[:4000], 'duration_seconds': duration,
        'like_count': _engagement_count(getattr(media, 'like_count', None)),
        'comment_count': _engagement_count(getattr(media, 'comment_count', None)),
        'thumbnail_url': _thumbnail(getattr(media, 'thumbnail_url', None)),
        'acquired_at': now.isoformat(), 'availability': 'ready',
        'acquisition_mode': 'live', 'playback': {'kind': 'mp4', 'asset_id': f'instagram:{identifier}:mp4',
            'url': url, 'expires_at': (now + timedelta(minutes=5)).isoformat(), 'mime_type': 'video/mp4'},
    }])[0]


class InstagramReelsProvider:
    def __init__(self, client, surface='discover', clock=None):
        if surface not in ('discover', 'connected'):
            raise ValueError('Choose discover or connected Reels.')
        self.client, self.surface = client, surface
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _request(self, endpoint, **kwargs):
        try:
            with quiet_instagram():
                # private_request() retries timeouts after a 60-second sleep, even
                # with transport retries disabled. This pinned primitive does one
                # request and never invokes checkpoint resolution or automatic login.
                return self.client._send_private_request(endpoint,
                    headers={'Authorization': self.client.authorization}, **kwargs)
        except Exception as error:
            raise provider_failure(error) from None

    def _normalize(self, rows):
        from instagrapi.extractors import extract_media_v1
        now, result = self.clock(), []
        for row in rows:
            try:
                with quiet_instagram():
                    item = normalize_reel(extract_media_v1(row), now)
                if item:
                    # SDK models default absent counts to zero; retain the raw
                    # provider's missing/hidden semantics before projection.
                    item['like_count'] = (None if row.get('like_and_view_counts_disabled')
                                          else _engagement_count(row.get('like_count')))
                    item['comment_count'] = _engagement_count(row.get('comment_count'))
                    result.append(item)
            except Exception:
                # One malformed/ad/non-video item must not discard a valid page.
                continue
        return normalized_items(result)

    def read_page(self, cursor=None):
        # Continuation belongs in this POST body. Query-only cursors can replay
        # the first provider batch despite a different returned cursor.
        response = self._request(f'clips/{self.surface}/', data={'max_id': cursor or ''})
        try:
            rows = response.get('items') or response.get('items_with_ads') or []
            paging = response.get('paging_info') or {}
            if not isinstance(rows, list) or len(rows) > 100 or not isinstance(paging, dict):
                raise ValueError()
            next_cursor = paging.get('max_id') or None
            if next_cursor is not None and not isinstance(next_cursor, str):
                raise ValueError()
            # Discover cursors accumulate viewed IDs and eventually exceed this
            # bounded server cache. Preserve this valid page; ending continuation
            # lets the next background refresh start a fresh stream instead of
            # retrying the same too-large cursor until the whole catalog expires.
            if next_cursor and (len(next_cursor) > 4096 or next_cursor == cursor):
                next_cursor = None
            if paging.get('more_available') is False:
                next_cursor = None
            media = [row['media'] for row in rows if isinstance(row, dict) and isinstance(row.get('media'), dict) and not row.get('is_ad')]
            return ProviderPage(self._normalize(media), next_cursor)
        except (ValueError, TypeError, AttributeError, KeyError):
            raise CatalogFailure(503, 'INSTAGRAM_INVALID_RESPONSE', 'Instagram returned an unreadable page. Retry shortly.') from None

    def refresh(self, provider_video_id):
        if not re.fullmatch(r'\d{1,32}', provider_video_id):
            raise ValueError('Invalid known Reel ID.')
        response = self._request(f'media/{provider_video_id}/info/')
        rows = response.get('items') if isinstance(response, dict) else None
        if not isinstance(rows, list) or len(rows) > 100:
            raise CatalogFailure(503, 'INSTAGRAM_INVALID_RESPONSE', 'Instagram returned unreadable playback information.')
        for item in self._normalize(rows):
            if item['provider_video_id'] == provider_video_id:
                return item
        raise CatalogFailure(410, 'PLAYBACK_UNAVAILABLE', 'This Instagram clip is no longer playable. Skip it.')

    def close(self):
        with quiet_instagram():
            for session in (self.client.private, self.client.public):
                with contextlib.suppress(Exception):
                    session.close()
