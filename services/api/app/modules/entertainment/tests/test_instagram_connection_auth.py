import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import httpx

from app.modules.auth.service import AuthFailure
from app.modules.entertainment import instagram_connection as connection
from app.modules.entertainment.experiments import preview_app

OWNER = '00000000-0000-4000-8000-000000000001'
OTHER = '00000000-0000-4000-8000-000000000002'
MARKER = 'SYNTHETIC_PROVIDER_PAYLOAD_MUST_NOT_ESCAPE'
PASSWORD = 'SYNTHETIC_PASSWORD_NEVER_SAVE'
URL = 'https://auth.example.test'
KEY = 'sb_publishable_synthetic'


class AppSigninTests(unittest.TestCase):
    def test_auth_rejections_have_fixed_codes_without_upstream_payloads(self):
        for status, code, expected in (
            (400, 'invalid_credentials', 'APP_INVALID_CREDENTIALS'),
            (400, 'email_not_confirmed', 'APP_EMAIL_NOT_CONFIRMED'),
            (429, 'over_request_rate_limit', 'APP_RATE_LIMITED'),
            (401, 'invalid_api_key', 'APP_AUTH_CONFIGURATION'),
            (500, None, 'APP_AUTH_UNAVAILABLE'),
            (403, MARKER, 'APP_LOGIN_REJECTED'),
            (400, {'untrusted': MARKER}, 'APP_LOGIN_REJECTED'),
        ):
            with self.subTest(status=status, expected=expected):
                transport = httpx.MockTransport(lambda request: httpx.Response(status,
                    json={'code': code, 'message': MARKER, 'password': PASSWORD}))
                with self.assertRaises(connection.ConnectionFailure) as failure:
                    connection.authenticate_app_owner(URL, KEY, 'synthetic@example.test', PASSWORD, transport=transport)
                self.assertEqual(failure.exception.code, expected)
                self.assertEqual(failure.exception.http_status, status)
                self.assertNotIn(MARKER, str(failure.exception))
                self.assertNotIn(PASSWORD, str(failure.exception))

    def test_timeouts_and_connection_failures_are_distinct_and_redacted(self):
        for error, expected in ((httpx.ReadTimeout(MARKER), 'APP_AUTH_TIMEOUT'),
                                (httpx.ConnectError(MARKER), 'APP_AUTH_UNAVAILABLE')):
            def network_failure(request):
                raise error
            with self.assertRaises(connection.ConnectionFailure) as failure:
                connection.authenticate_app_owner(URL, KEY, 'synthetic@example.test', PASSWORD,
                    transport=httpx.MockTransport(network_failure))
            self.assertEqual(failure.exception.code, expected)
            self.assertNotIn(MARKER, str(failure.exception))

    def test_owner_comes_from_canonical_verifier_not_grant_payload_or_metadata(self):
        observed = []
        class Verifier:
            async def verify_access_token(self, token):
                observed.append(token)
                return {'user_id': OWNER}
        transport = httpx.MockTransport(lambda request: httpx.Response(200,
            json={'access_token': MARKER, 'user': {'id': OTHER}, 'user_metadata': {'user_id': OTHER}}))
        owner = connection.authenticate_app_owner(URL, KEY, 'synthetic@example.test', PASSWORD,
            transport=transport, verifier=Verifier())
        self.assertEqual(owner, OWNER)
        self.assertEqual(observed, [MARKER])

    def test_malformed_signin_and_failed_canonical_verification_never_bind_an_owner(self):
        for body in ({}, [], {'access_token': 123}, {'access_token': ''}):
            with self.assertRaises(connection.ConnectionFailure) as failure:
                connection.authenticate_app_owner(URL, KEY, 'synthetic@example.test', PASSWORD,
                    transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
            self.assertEqual(failure.exception.code, 'APP_AUTH_INVALID_RESPONSE')
        class Verifier:
            async def verify_access_token(self, token):
                raise AuthFailure(401, 'AUTH_INVALID', MARKER)
        with self.assertRaises(connection.ConnectionFailure) as failure:
            connection.authenticate_app_owner(URL, KEY, 'synthetic@example.test', PASSWORD,
                transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'access_token': MARKER})),
                verifier=Verifier())
        self.assertEqual(failure.exception.code, 'APP_SESSION_REJECTED')
        self.assertNotIn(MARKER, str(failure.exception))

    def test_url_only_override_retains_configured_mobile_publishable_key(self):
        with patch.dict('os.environ', {'SUPABASE_URL': URL}, clear=True), \
             patch.object(preview_app, 'mobile_configuration', return_value={
                 'EXPO_PUBLIC_SUPABASE_URL': URL, 'EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY': KEY}):
            self.assertEqual(preview_app.supabase_configuration(), (URL, KEY))

    def test_placeholder_or_privileged_key_configuration_fails_before_password_prompt(self):
        with patch.object(preview_app, 'supabase_configuration', return_value=(URL, 'service-role-test-only')), \
             patch('builtins.input') as email, patch('getpass.getpass') as password:
            with self.assertRaises(connection.ConnectionFailure) as failure:
                connection.app_owner()
        self.assertEqual(failure.exception.code, 'APP_AUTH_CONFIGURATION')
        email.assert_not_called(); password.assert_not_called()


class StageReportTests(unittest.TestCase):
    def test_app_signin_rejection_records_stage_and_safe_http_status_before_instagram(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'connection.json'
            output = io.StringIO()
            with patch('sys.argv', ['connect', '--connection', str(path)]), \
                 patch('sys.stdin.isatty', return_value=True), \
                 patch.object(connection, 'app_owner', side_effect=connection.ConnectionFailure(
                     'APP_INVALID_CREDENTIALS', 'Supabase rejected the app login.', 400)), \
                 patch.object(connection, 'make_instagram_client') as instagram, \
                 patch('getpass.getpass') as prompts, contextlib.redirect_stdout(output):
                self.assertEqual(connection.main(), 1)
            report = json.loads((path.parent / 'report.json').read_text())
            self.assertEqual(report['stage'], 'app_login')
            self.assertEqual(report['error_code'], 'APP_INVALID_CREDENTIALS')
            self.assertEqual(report['http_status'], 400)
            self.assertFalse(path.exists())
            instagram.assert_not_called(); prompts.assert_not_called()

    def test_unexpected_app_failure_keeps_details_private_and_does_not_attempt_instagram(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'connection.json'
            output = io.StringIO()
            with patch('sys.argv', ['connect', '--connection', str(path)]), \
                 patch('sys.stdin.isatty', return_value=True), \
                 patch.object(connection, 'app_owner', side_effect=RuntimeError(MARKER)), \
                 patch.object(connection, 'make_instagram_client') as instagram, \
                 contextlib.redirect_stdout(output):
                self.assertEqual(connection.main(), 1)
            report_text = (path.parent / 'report.json').read_text()
            report = json.loads(report_text)
            self.assertEqual(report['error_code'], 'APP_LOGIN_FAILED')
            self.assertEqual(report['stage'], 'app_login')
            self.assertNotIn(MARKER, report_text + output.getvalue())
            instagram.assert_not_called()

    def test_operator_uuid_skips_app_signin_and_instagram_rejection_is_not_misreported(self):
        calls = []
        class BadPassword(Exception):
            pass
        class Client:
            user_id = None
            private = SimpleNamespace(close=lambda: None)
            public = SimpleNamespace(close=lambda: None)
            def get_settings(self):
                return {'uuids': {'phone_id': 'synthetic-device'}}
            def login(self, *args, **kwargs):
                calls.append(1)
                print(MARKER)
                raise BadPassword(MARKER)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'connection.json'
            output = io.StringIO()
            with patch('sys.argv', ['connect', '--connection', str(path), '--owner-user-id', OWNER]), \
                 patch('sys.stdin.isatty', return_value=True), \
                 patch.object(connection, 'app_owner') as app_signin, \
                 patch.object(connection, 'make_instagram_client', return_value=Client()), \
                 patch('getpass.getpass', side_effect=['synthetic', PASSWORD, '']), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(connection.main(), 1)
            text = (path.parent / 'report.json').read_text()
            report = json.loads(text)
            self.assertEqual(report['stage'], 'instagram_login')
            self.assertEqual(report['error_code'], 'INSTAGRAM_LOGIN_REJECTED')
            self.assertEqual(report['provider_error_type'], 'BadPassword')
            self.assertEqual(len(calls), 1)
            self.assertFalse(path.exists())
            self.assertNotIn(MARKER, text + output.getvalue())
            self.assertNotIn(PASSWORD, text + output.getvalue())
            app_signin.assert_not_called()


class DeviceProfileTests(unittest.TestCase):
    def test_local_profile_errors_are_not_reported_as_instagram_rejections(self):
        settings = {'uuids': {'phone_id': 'synthetic-device'}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'device.json'
            with patch.object(connection, 'write_private', side_effect=PermissionError(MARKER)):
                with self.assertRaises(connection.ConnectionFailure) as failure:
                    connection.save_device_profile(path, OWNER, 'synthetic', 'discover', settings)
            self.assertEqual(failure.exception.code, 'LOCAL_PROFILE_UNAVAILABLE')
            self.assertNotIn(MARKER, str(failure.exception))
            connection.save_device_profile(path, OWNER, 'synthetic', 'discover', settings)
            path.chmod(0o644)
            with self.assertRaises(connection.ConnectionFailure) as failure:
                connection.load_device_profile(path, OWNER, 'synthetic')
            self.assertEqual(failure.exception.code, 'LOCAL_PROFILE_UNAVAILABLE')

    def test_pending_device_reuses_identity_without_auth_cookies_passwords_or_plain_username(self):
        settings = {'uuids': {'phone_id': 'synthetic-stable-device'},
                    'cookies': {'csrftoken': 'synthetic-csrf', 'sessionid': MARKER, 'ds_user_id': OTHER},
                    'authorization_data': {'sessionid': MARKER}, 'password': PASSWORD}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'connection.json'
            path = connection.device_profile_path(target, OWNER, 'synthetic_username')
            connection.save_device_profile(path, OWNER, 'synthetic_username', 'discover', settings)
            restored = connection.load_device_profile(path, OWNER, 'SYNTHETIC_USERNAME')
            self.assertEqual(restored['uuids'], settings['uuids'])
            self.assertEqual(restored['cookies'], {'csrftoken': 'synthetic-csrf'})
            self.assertEqual(restored['authorization_data'], {})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            text = path.read_text()
            for forbidden in (MARKER, PASSWORD, 'synthetic_username', OTHER):
                self.assertNotIn(forbidden, text)
            for owner, username in ((OTHER, 'synthetic_username'), (OWNER, 'different_username')):
                self.assertNotEqual(connection.device_profile_path(target, owner, username), path)
                with self.assertRaises(connection.ConnectionFailure):
                    connection.load_device_profile(path, owner, username)

    def test_manual_retry_after_checkpoint_restores_same_device_and_preserves_no_ready_session(self):
        seen_settings = []
        class ChallengeRequired(Exception):
            pass
        class Client:
            user_id = None
            private = SimpleNamespace(close=lambda: None)
            public = SimpleNamespace(close=lambda: None)
            def __init__(self, settings):
                seen_settings.append(settings)
            def get_settings(self):
                return {'uuids': {'phone_id': 'synthetic-stable-device'}, 'cookies': {'sessionid': MARKER}}
            def login(self, *args, **kwargs):
                raise ChallengeRequired(MARKER)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'connection.json'
            for attempt in range(2):
                output = io.StringIO()
                with patch('sys.argv', ['connect', '--connection', str(path), '--owner-user-id', OWNER]), \
                     patch('sys.stdin.isatty', return_value=True), \
                     patch.object(connection, 'make_instagram_client', side_effect=Client), \
                     patch('getpass.getpass', side_effect=['synthetic_username', PASSWORD, '']), \
                     contextlib.redirect_stdout(output):
                    self.assertEqual(connection.main(), 1)
                report_text = (path.parent / 'report.json').read_text()
                report = json.loads(report_text)
                self.assertEqual(report['error_code'], 'INSTAGRAM_CHECKPOINT_REQUIRED')
                self.assertEqual(report['device_profile_reused'], bool(attempt))
                self.assertTrue(report['device_profile_saved'])
                self.assertFalse(path.exists())
                self.assertNotIn(MARKER, report_text + output.getvalue())
            self.assertIsNone(seen_settings[0])
            self.assertEqual(seen_settings[1]['uuids']['phone_id'], 'synthetic-stable-device')
            self.assertEqual(seen_settings[1]['authorization_data'], {})
