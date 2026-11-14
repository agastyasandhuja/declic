"""Supabase-backed app-token verification; never trusts a caller-selected user ID."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from jsonschema import Draft7Validator, FormatChecker
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[5]
USER_VALIDATOR = Draft7Validator(json.loads((ROOT / 'contracts/schemas/identity/current-user.v1.schema.json').read_text()), format_checker=FormatChecker())


class AuthFailure(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


class SupabaseVerifier:
    def __init__(self, url: str, publishable_key: str, transport=None):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment or not publishable_key.strip():
            raise ValueError('Supabase verification requires a configured HTTPS origin.')
        self.url, self.key, self.transport = url.rstrip('/'), publishable_key, transport

    async def verify_access_token(self, token: str) -> dict:
        if not token or len(token) > 16384:
            raise AuthFailure(401, 'AUTH_REQUIRED', 'Sign in to access your private feed.')
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False, transport=self.transport) as client:
                response = await client.get(f'{self.url}/auth/v1/user', headers={'apikey': self.key, 'Authorization': f'Bearer {token}'})
        except httpx.HTTPError:
            raise AuthFailure(503, 'AUTH_UNAVAILABLE', 'Account verification is temporarily unavailable. Retry.') from None
        if response.status_code in (401, 403):
            raise AuthFailure(401, 'AUTH_INVALID', 'Your session is invalid or expired. Sign in again.')
        if response.status_code != 200:
            raise AuthFailure(503, 'AUTH_UNAVAILABLE', 'Account verification is temporarily unavailable. Retry.')
        try:
            data = response.json()
            # Subject comes from the Auth server, never editable user_metadata.
            user = {'user_id': data['id'], 'email': data.get('email'), 'display_name': None,
                    'timezone': 'UTC', 'created_at': data['created_at']}
            USER_VALIDATOR.validate(user)
            if datetime.fromisoformat(user['created_at'].replace('Z', '+00:00')).tzinfo is None:
                raise ValueError('Account timestamp requires an explicit zone.')
        except (ValueError, KeyError, TypeError, ValidationError):
            # Only a fixed message crosses the boundary; provider responses stay private.
            raise AuthFailure(503, 'AUTH_INVALID_RESPONSE', 'Account verification returned an invalid response.') from None
        return user
