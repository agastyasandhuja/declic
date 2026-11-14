"""Opaque cursors bound to authenticated subject, query and immutable batch revision."""
import base64
import hashlib
import hmac
import json
import secrets


class CursorError(ValueError):
    def __init__(self, stale=False):
        self.stale = stale
        super().__init__('Stale catalog cursor.' if stale else 'Invalid catalog cursor.')


class CursorCodec:
    def __init__(self, secret: bytes | None = None):
        self.secret = secret or secrets.token_bytes(32)
        if len(self.secret) < 32:
            raise ValueError('Cursor signing requires at least 32 bytes.')

    def encode(self, offset, subject, revision, limit):
        payload = json.dumps([offset, subject, revision, limit], separators=(',', ':')).encode()
        signature = hmac.digest(self.secret, payload, 'sha256')
        return base64.urlsafe_b64encode(signature + payload).decode().rstrip('=')

    def decode(self, cursor, subject, revision, limit):
        try:
            if not isinstance(cursor, str) or len(cursor) > 2048:
                raise ValueError()
            raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
            signature, payload = raw[:32], raw[32:]
            if not hmac.compare_digest(signature, hmac.digest(self.secret, payload, 'sha256')):
                raise ValueError()
            offset, owner, batch, page_size = json.loads(payload)
            if owner != subject or page_size != limit or type(offset) is not int or offset <= 0:
                raise ValueError()
        except (ValueError, TypeError, UnicodeError):
            raise CursorError() from None
        if batch != revision:
            raise CursorError(stale=True)
        return offset


def batch_revision(items):
    return hashlib.sha256(json.dumps(items, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
