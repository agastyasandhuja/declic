"""Local operator setup and restoration; not a mobile login or token-collection API."""
from __future__ import annotations

import argparse
import asyncio
import getpass
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import sys
import tempfile
from datetime import datetime, timezone
from uuid import UUID

import httpx

from app.modules.auth.service import AuthFailure, SupabaseVerifier
from .instagram import InstagramReelsProvider, make_instagram_client, provider_failure, quiet_instagram
from .live import LiveInstagramCatalog
from .instagram_login import login_interactively, login_with_browser_session
from .service import CatalogFailure

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_CONNECTION = ROOT / '.local/instagram-live/connection.json'
SESSION_FIELDS = {'uuids', 'mid', 'ig_u_rur', 'ig_www_claim', 'authorization_data', 'cookies',
                  'last_login', 'device_settings', 'user_agent', 'country', 'country_code',
                  'locale', 'timezone_offset', 'timezone_name', 'push_disabled', 'usdid'}
DEVICE_FIELDS = {'uuids', 'mid', 'device_settings', 'user_agent', 'country', 'country_code',
                 'locale', 'timezone_offset', 'timezone_name', 'push_disabled'}
DEVICE_COOKIES = {'mid', 'csrftoken', 'ig_did', 'ig_nrcb'}
DEVICE_REGISTRATION_FIELDS = {'usdid', 'kid', 'private_key', 'registered'}
LOGIN_ERRORS = {
    'ChallengeRequired': ('INSTAGRAM_CHECKPOINT_REQUIRED', 'Complete the verification in the official Instagram app, then retry manually.'),
    'AccountContactPointRequired': ('INSTAGRAM_CHECKPOINT_REQUIRED', 'Complete the account verification in the official Instagram app.'),
    'TwoFactorRequired': ('INSTAGRAM_TWO_FACTOR_REQUIRED', 'Enter a current two-factor code at the local hidden prompt; never in chat.'),
    'BadPassword': ('INSTAGRAM_LOGIN_REJECTED', 'Instagram rejected this login. Review the account and password locally before retrying.'),
    'BadCredentials': ('INSTAGRAM_LOGIN_REJECTED', 'Check the Instagram login locally before retrying.'),
    'ClientNeedsUpgradeError': ('INSTAGRAM_CLIENT_REJECTED', 'Instagram rejected this SDK client login. Review the account locally; do not loop attempts.'),
    'AccountSuspended': ('INSTAGRAM_ACCOUNT_UNAVAILABLE', 'Review this account in the official Instagram app.'),
    'FeedbackRequired': ('INSTAGRAM_RATE_LIMITED', 'Instagram restricted this login. Review the account and wait before another attempt.'),
    'SentryBlock': ('INSTAGRAM_RATE_LIMITED', 'Instagram restricted this login. Review the account and wait before another attempt.'),
}


class ConnectionFailure(Exception):
    """Only fixed public diagnostics, never an upstream response or input value."""
    def __init__(self, code, message, http_status=None):
        self.code, self.message, self.http_status = code, message, http_status
        super().__init__(message)


APP_ERRORS = {
    'invalid_credentials': ('APP_INVALID_CREDENTIALS', 'Supabase rejected the app email/password. Use the app login, separate from Instagram.'),
    'email_not_confirmed': ('APP_EMAIL_NOT_CONFIRMED', 'Confirm the app account email, then return to the app and sign in.'),
    'over_request_rate_limit': ('APP_RATE_LIMITED', 'Supabase is limiting app sign-in requests. Wait before trying again.'),
    'over_email_send_rate_limit': ('APP_RATE_LIMITED', 'Supabase is limiting auth requests. Wait before trying again.'),
    'user_banned': ('APP_ACCOUNT_UNAVAILABLE', 'This app account cannot sign in. Review the account in Supabase.'),
    'invalid_api_key': ('APP_AUTH_CONFIGURATION', 'Check the Supabase project URL and publishable key.'),
    'request_timeout': ('APP_AUTH_TIMEOUT', 'App sign-in timed out. Check the connection and retry locally.'),
}


def authenticate_app_owner(url, key, email, password, *, transport=None, verifier=None):
    """One canonical password grant, then verified-subject lookup; no retries/storage."""
    if not email or not password:
        raise ConnectionFailure('APP_INPUT_REQUIRED', 'Enter the app account email/password, or use its verified UUID.')
    try:
        with httpx.Client(timeout=10, follow_redirects=False, transport=transport) as client:
            response = client.post(f'{url.rstrip("/")}/auth/v1/token?grant_type=password',
                                   headers={'apikey': key}, json={'email': email, 'password': password})
    except httpx.TimeoutException:
        raise ConnectionFailure('APP_AUTH_TIMEOUT', 'App sign-in timed out. Check the connection and retry locally.') from None
    except httpx.HTTPError:
        raise ConnectionFailure('APP_AUTH_UNAVAILABLE', 'Unable to reach Supabase. Check the connection before retrying.') from None
    try:
        body = response.json()
    except ValueError:
        body = None
    if response.status_code != 200:
        upstream_code = body.get('code') or body.get('error_code') if isinstance(body, dict) else None
        diagnostic = APP_ERRORS.get(upstream_code) if isinstance(upstream_code, str) else None
        if diagnostic is None:
            diagnostic = ('APP_AUTH_UNAVAILABLE', 'Supabase is temporarily unavailable. Retry locally later.') if response.status_code >= 500 else ('APP_LOGIN_REJECTED', 'Supabase rejected the app sign-in. Check the app account or use its verified UUID.')
        raise ConnectionFailure(*diagnostic, http_status=response.status_code)
    token = body.get('access_token') if isinstance(body, dict) else None
    if not isinstance(token, str) or not token:
        raise ConnectionFailure('APP_AUTH_INVALID_RESPONSE', 'Supabase returned an unreadable sign-in result.', 200)
    try:
        user = asyncio.run((verifier or SupabaseVerifier(url, key)).verify_access_token(token))
        return str(UUID(user['user_id']))
    except AuthFailure as error:
        code = 'APP_AUTH_UNAVAILABLE' if error.code == 'AUTH_UNAVAILABLE' else 'APP_SESSION_REJECTED'
        raise ConnectionFailure(code, 'The app session could not be verified. Retry locally or use the verified app UUID.') from None
    except (ValueError, KeyError, TypeError):
        raise ConnectionFailure('APP_AUTH_INVALID_RESPONSE', 'Supabase returned an invalid app identity.') from None


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        staged = Path(stream.name)
        try:
            json.dump(value, stream)
            stream.write('\n')
        except BaseException:
            staged.unlink(missing_ok=True)
            raise
    staged.replace(path)


def save_connection(path, owner, settings, surface):
    owner = str(UUID(owner))
    if surface not in ('discover', 'connected'):
        raise ValueError('Invalid Instagram surface.')
    session = {key: value for key, value in settings.items() if key in SESSION_FIELDS}
    if not session.get('authorization_data') and not session.get('cookies'):
        raise ValueError('No authenticated Instagram session.')
    write_private(path, {'schema_version': '1', 'owner_user_id': owner, 'surface': surface,
                        'connected_at': datetime.now(timezone.utc).isoformat(), 'session': session})


def load_connection(path):
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077
                or metadata.st_uid != os.getuid() or metadata.st_size > 131072):
            raise ValueError()
        with os.fdopen(descriptor) as stream:
            descriptor = None
            value = json.load(stream)
        if (value['schema_version'] != '1' or value['surface'] not in ('discover', 'connected')
                or not isinstance(value['session'], dict)):
            raise ValueError()
        value['owner_user_id'] = str(UUID(value['owner_user_id']))
        return value
    except (OSError, ValueError, KeyError, TypeError):
        raise CatalogFailure(409, 'INSTAGRAM_NOT_CONNECTED',
                              'Connect Instagram locally before opening the live feed.') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def login_hash(username):
    return hashlib.sha256(username.strip().casefold().encode()).hexdigest()


def device_profile_path(connection_path, owner, username):
    identifier = hashlib.sha256(f'{str(UUID(owner))}:{login_hash(username)}'.encode()).hexdigest()
    return connection_path.parent / f'device-{identifier}.json'


def device_settings(settings):
    result = {key: value for key, value in settings.items() if key in DEVICE_FIELDS}
    if not isinstance(result.get('uuids'), dict) or not result['uuids']:
        raise ConnectionFailure('INSTAGRAM_DEVICE_UNAVAILABLE', 'The SDK did not provide a reusable device profile.')
    # Retain device/CSRF cookies only. Pending profiles cannot authenticate a
    # user or trigger the SDK's automatic expired-session login path.
    cookies = settings.get('cookies') or {}
    result['cookies'] = {key: value for key, value in cookies.items() if key in DEVICE_COOKIES}
    result['authorization_data'] = {}
    # A stable device also needs its SDK registration key, not only UUIDs.
    # This device credential cannot identify an account; keep it in this same
    # private server-side file and exclude all unrelated nested fields.
    registration = settings.get('usdid')
    if isinstance(registration, dict) and registration.get('private_key'):
        if any(not isinstance(registration.get(key), str) or len(registration[key]) > 16384
               for key in ('usdid', 'kid', 'private_key')) or type(registration.get('registered')) is not bool:
            raise ConnectionFailure('INSTAGRAM_DEVICE_UNAVAILABLE', 'The SDK returned an invalid device registration profile.')
        result['usdid'] = {key: registration[key] for key in DEVICE_REGISTRATION_FIELDS}
    return result


def save_device_profile(path, owner, username, surface, settings):
    value = {'schema_version': '1', 'owner_user_id': str(UUID(owner)),
             'login_hash': login_hash(username), 'surface': surface,
             'session': device_settings(settings)}
    try:
        write_private(path, value)
    except (OSError, TypeError, ValueError):
        raise ConnectionFailure('LOCAL_PROFILE_UNAVAILABLE', 'The local device profile could not be saved. Review local file permissions.') from None


def load_device_profile(path, owner, username):
    if not path.exists():
        return None
    try:
        value = load_connection(path)
    except CatalogFailure:
        raise ConnectionFailure('LOCAL_PROFILE_UNAVAILABLE', 'The local device profile could not be read securely. Review local file permissions.') from None
    if value['owner_user_id'] != str(UUID(owner)) or value.get('login_hash') != login_hash(username):
        raise ConnectionFailure('INSTAGRAM_DEVICE_MISMATCH', 'The saved device belongs to another connection. Review local setup.')
    return device_settings(value['session'])


def open_live_catalog(path=DEFAULT_CONNECTION, **kwargs):
    connection = load_connection(Path(path))
    client = make_instagram_client(connection['session'])
    if not client.user_id:
        InstagramReelsProvider(client).close()
        raise CatalogFailure(409, 'INSTAGRAM_NOT_CONNECTED', 'Reconnect Instagram locally.')
    return LiveInstagramCatalog(connection['owner_user_id'],
                                InstagramReelsProvider(client, connection['surface']), **kwargs)


def app_owner():
    # Canonical Auth calls, no second account/password store and no saved app token.
    from .experiments.preview_app import supabase_configuration
    try:
        url, key = supabase_configuration()
        verifier = SupabaseVerifier(url, key)
        if 'your-project' in url or not key.startswith('sb_publishable_') or 'replace_me' in key:
            raise ValueError()
    except (OSError, ValueError, KeyError):
        raise ConnectionFailure('APP_AUTH_CONFIGURATION', 'Configure the Supabase URL and publishable key before signing in.') from None
    email = input('App account email (Supabase, separate from Instagram): ').strip()
    password = getpass.getpass('App account password (hidden, not saved): ')
    try:
        return authenticate_app_owner(url, key, email, password, verifier=verifier)
    finally:
        password = ''


def main():
    parser = argparse.ArgumentParser(description='Connect an Instagram session privately on this Mac; never collects credentials through mobile.')
    parser.add_argument('--connection', type=Path, default=DEFAULT_CONNECTION)
    parser.add_argument('--owner-user-id', help='Trusted operator only: UUID copied from the signed-in app, instead of local app login.')
    parser.add_argument('--surface', choices=('discover', 'connected'), default='discover')
    parser.add_argument('--check', action='store_true', help='Verify two pages using the saved session, without logging in again.')
    parser.add_argument('--browser-session', action='store_true', help='Use a sessionid cookie from your own signed-in browser at a hidden local prompt; no Instagram password login.')
    args = parser.parse_args()
    if not args.check and not sys.stdin.isatty():
        parser.error('Run this in your own Terminal for hidden credential prompts.')
    provider, client, password, session_id = None, None, '', ''
    report = {'schema_version': '1', 'started_at': datetime.now(timezone.utc).isoformat(),
              'authenticated': False, 'pages_retrieved': 0, 'unique_reels': 0, 'has_more': False,
              'stage': 'setup'}
    old_alarm = None
    try:
        if args.check:
            report['stage'] = 'restore_instagram_session'
            connection = load_connection(args.connection)
            client = make_instagram_client(connection['session'])
            surface = connection['surface']
        else:
            print('This saves an owner-only Instagram session under .local/instagram-live; passwords are not saved.')
            report['stage'] = 'app_binding' if args.owner_user_id else 'app_login'
            if args.owner_user_id:
                try:
                    owner = str(UUID(args.owner_user_id))
                except ValueError:
                    raise ConnectionFailure('APP_INVALID_USER_ID', 'Copy the verified App user ID as a UUID, not an email.') from None
            else:
                owner = app_owner()
            report['stage'] = 'instagram_login'
            username = getpass.getpass('Instagram username (hidden): ').strip()
            if not username:
                raise ConnectionFailure('INSTAGRAM_INPUT_REQUIRED', 'Enter the Instagram username locally.')
            profile_path = device_profile_path(args.connection, owner, username)
            profile = load_device_profile(profile_path, owner, username)
            report['device_profile_reused'] = profile is not None
            client = make_instagram_client(profile)
            with quiet_instagram():
                initial_settings = client.get_settings()
            # Persist identity before the first network login, including when a
            # challenge interrupts it. A later manual retry uses the same device.
            save_device_profile(profile_path, owner, username, args.surface, initial_settings)
            report['device_profile_saved'] = True
            if args.browser_session:
                session_id = getpass.getpass('Instagram sessionid cookie from your own signed-in browser (hidden; never paste in chat): ').strip()
            else:
                password = getpass.getpass('Instagram password (hidden): ')
            if not (session_id if args.browser_session else password):
                raise ConnectionFailure('INSTAGRAM_INPUT_REQUIRED', 'Enter the Instagram credentials locally.')
            def deadline(_signum, _frame):
                raise TimeoutError()
            if hasattr(signal, 'SIGALRM'):
                old_alarm = signal.signal(signal.SIGALRM, deadline)
                signal.alarm(180)
            try:
                settings = (login_with_browser_session(client, username, session_id, report)
                            if args.browser_session else login_interactively(client, username, password, report))
            except BaseException:
                # Best-effort device updates must never mask the typed login
                # rejection. Raw challenge responses and authentication cookies
                # are deliberately excluded from this pending profile.
                try:
                    with quiet_instagram():
                        latest_settings = client.get_settings()
                    save_device_profile(profile_path, owner, username, args.surface, latest_settings)
                except Exception:
                    pass
                raise
            save_device_profile(profile_path, owner, username, args.surface, settings)
            report['stage'] = 'save_instagram_session'
            save_connection(args.connection, owner, settings, args.surface)
            surface = args.surface
            print('Saved the Instagram session locally with mode 0600; bound to your app account.')
        provider = InstagramReelsProvider(client, surface)
        report['authenticated'] = bool(client.user_id)
        if not report['authenticated']:
            raise CatalogFailure(409, 'INSTAGRAM_NOT_CONNECTED', 'Reconnect Instagram locally.')
        report['stage'] = 'reels'
        seen, cursor = set(), None
        for _ in range(2):
            page = provider.read_page(cursor)
            seen.update(item['provider_video_id'] for item in page.items)
            report['pages_retrieved'] += 1
            next_cursor = page.next_cursor
            report['has_more'] = bool(next_cursor and next_cursor != cursor)
            if not report['has_more']:
                break
            cursor = next_cursor
        report['unique_reels'] = len(seen)
        report['status'] = 'completed'
        report['stage'] = 'completed'
        print(f"Verified {report['pages_retrieved']} live page(s), {len(seen)} unique Reels; continuation available: {report['has_more']}.")
        print('Session secrets and personalized metadata were not printed. Phone playback is a separate check.')
        return 0
    except (Exception, KeyboardInterrupt) as error:
        if isinstance(error, (ConnectionFailure, CatalogFailure)):
            failure = error
        elif isinstance(error, KeyboardInterrupt):
            failure = ConnectionFailure('CANCELLED', 'Local setup was cancelled.')
        elif report['stage'] in {'instagram_login', 'verify_instagram_session'}:
            kind = type(error).__name__
            if kind in LOGIN_ERRORS or kind in {'ClientError', 'ClientConnectionError', 'ClientRequestTimeout',
                    'ClientJSONDecodeError', 'ClientIncompleteReadError', 'ClientThrottledError',
                    'RateLimitError', 'PleaseWaitFewMinutes', 'ClientUnauthorizedError', 'ClientForbiddenError', 'LoginRequired'}:
                report['provider_error_type'] = kind
            diagnostic = LOGIN_ERRORS.get(kind)
            if diagnostic:
                failure = ConnectionFailure(*diagnostic)
            else:
                failure = provider_failure(error)
        elif report['stage'] == 'app_login':
            failure = ConnectionFailure('APP_LOGIN_FAILED', 'The app sign-in failed. Check the app account or use its verified UUID.')
        else:
            failure = ConnectionFailure('CONNECTION_FAILED', 'Local setup failed. Share only the stage and safe error code.')
        report.update(status='failed', error_code=failure.code)
        if isinstance(failure, ConnectionFailure) and failure.http_status is not None:
            report['http_status'] = failure.http_status
        print(f"Stopped during {report['stage']}: {failure.code}. {failure.message}")
        if report.get('login_request_phase'):
            print(f"Login request step: {report['login_request_phase']}; HTTP status: {report.get('provider_http_status', 'unavailable')}.")
        print('No automatic Instagram login or checkpoint retries. Do not paste passwords, cookies or raw errors into chat.')
        return 1
    finally:
        password = session_id = ''
        if old_alarm is not None:
            signal.alarm(0); signal.signal(signal.SIGALRM, old_alarm)
        if provider:
            provider.close()
        elif client is not None:
            InstagramReelsProvider(client).close()
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        write_private(args.connection.parent / 'report.json', report)


if __name__ == '__main__':
    raise SystemExit(main())
