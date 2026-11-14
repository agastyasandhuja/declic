"""Local operator setup and restoration; not a mobile login or token-collection API."""
from __future__ import annotations

import argparse
import asyncio
import getpass
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

from app.modules.auth.service import SupabaseVerifier
from .instagram import InstagramReelsProvider, make_instagram_client, quiet_instagram
from .live import LiveInstagramCatalog
from .service import CatalogFailure

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_CONNECTION = ROOT / '.local/instagram-live/connection.json'
SESSION_FIELDS = {'uuids', 'mid', 'ig_u_rur', 'ig_www_claim', 'authorization_data', 'cookies',
                  'last_login', 'device_settings', 'user_agent', 'country', 'country_code',
                  'locale', 'timezone_offset', 'timezone_name', 'push_disabled', 'usdid'}


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
    from .experiments.preview_app import mobile_configuration
    values = mobile_configuration() if not os.environ.get('SUPABASE_URL') else {}
    url = os.environ.get('SUPABASE_URL') or values['EXPO_PUBLIC_SUPABASE_URL']
    key = os.environ.get('SUPABASE_PUBLISHABLE_KEY') or values['EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY']
    verifier = SupabaseVerifier(url, key)
    email = input('App account email (Supabase, separate from Instagram): ').strip()
    password = getpass.getpass('App account password (hidden, not saved): ')
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.post(f'{url.rstrip("/")}/auth/v1/token?grant_type=password',
                                   headers={'apikey': key}, json={'email': email, 'password': password})
        if response.status_code != 200:
            raise ValueError('Unable to authenticate the app account.')
        token = response.json()['access_token']
        return asyncio.run(verifier.verify_access_token(token))['user_id']
    finally:
        password = ''


def main():
    parser = argparse.ArgumentParser(description='Connect an Instagram session privately on this Mac; never collects credentials through mobile.')
    parser.add_argument('--connection', type=Path, default=DEFAULT_CONNECTION)
    parser.add_argument('--owner-user-id', help='Trusted operator only: UUID copied from the signed-in app, instead of local app login.')
    parser.add_argument('--surface', choices=('discover', 'connected'), default='discover')
    parser.add_argument('--check', action='store_true', help='Verify two pages using the saved session, without logging in again.')
    args = parser.parse_args()
    if not args.check and not sys.stdin.isatty():
        parser.error('Run this in your own Terminal for hidden credential prompts.')
    provider, client, password, code = None, None, '', ''
    report = {'schema_version': '1', 'started_at': datetime.now(timezone.utc).isoformat(),
              'authenticated': False, 'pages_retrieved': 0, 'unique_reels': 0, 'has_more': False}
    old_alarm = None
    try:
        if args.check:
            connection = load_connection(args.connection)
            client = make_instagram_client(connection['session'])
            surface = connection['surface']
        else:
            print('This saves an owner-only Instagram session under .local/instagram-live; passwords are not saved.')
            owner = str(UUID(args.owner_user_id)) if args.owner_user_id else app_owner()
            username = getpass.getpass('Instagram username (hidden): ').strip()
            password = getpass.getpass('Instagram password (hidden): ')
            code = getpass.getpass('Current Instagram 2FA code, or Enter if disabled (hidden): ').strip()
            if not username or not password:
                raise ValueError('Instagram credentials are required.')
            client = make_instagram_client()
            def deadline(_signum, _frame):
                raise TimeoutError()
            if hasattr(signal, 'SIGALRM'):
                old_alarm = signal.signal(signal.SIGALRM, deadline)
                signal.alarm(180)
            with quiet_instagram():
                accepted = client.login(username, password, verification_code=code)
                settings = client.get_settings()
            if not accepted or not client.user_id:
                raise ValueError('No authenticated session.')
            save_connection(args.connection, owner, settings, args.surface)
            surface = args.surface
            print('Saved the Instagram session locally with mode 0600; bound to your app account.')
        provider = InstagramReelsProvider(client, surface)
        report['authenticated'] = bool(client.user_id)
        if not report['authenticated']:
            raise CatalogFailure(409, 'INSTAGRAM_NOT_CONNECTED', 'Reconnect Instagram locally.')
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
        print(f"Verified {report['pages_retrieved']} live page(s), {len(seen)} unique Reels; continuation available: {report['has_more']}.")
        print('Session secrets and personalized metadata were not printed. Phone playback is a separate check.')
        return 0
    except (Exception, KeyboardInterrupt) as error:
        report.update(status='failed', error_code=error.code if isinstance(error, CatalogFailure) else 'CONNECTION_FAILED')
        print(f"Stopped: {report['error_code']}. No automatic Instagram login or checkpoint retries.")
        print('Check your app login or review Instagram locally. Do not paste passwords, cookies or raw errors into chat.')
        return 1
    finally:
        password = code = ''
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
