import contextlib
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.modules.entertainment.instagram import InstagramReelsProvider, make_instagram_client
from app.modules.entertainment.instagram_connection import device_settings
from app.modules.entertainment.instagram_login import login_interactively, login_with_browser_session, single_attempt_requests
from app.modules.entertainment.service import CatalogFailure

PAYLOAD = 'SYNTHETIC_PRIVATE_RESPONSE_NEVER_EXPORT'
PASSWORD = 'SYNTHETIC_PASSWORD_NEVER_EXPORT'
CODE = '135791'
CONTEXT = 'SYNTHETIC_TWO_FACTOR_CONTEXT_NEVER_EXPORT'


class LoginTests(unittest.TestCase):
    def client(self):
        client = SimpleNamespace(user_id=123, authorization='synthetic-authorization')
        client.login = Mock(return_value=True)
        client.get_settings = Mock(return_value={'cookies': {'sessionid': PAYLOAD}})
        client.private_request = Mock(side_effect=AssertionError('Retry-capable SDK helper must not run'))
        client._send_private_request = Mock(return_value={'user': {'pk': 123}})
        return client

    def test_no_code_prompt_without_two_factor_and_session_requires_current_user_check(self):
        client = self.client()
        read_code = Mock(side_effect=AssertionError('No code requested'))
        report = {}
        settings = login_interactively(client, 'synthetic', PASSWORD, report, read_code=read_code)
        client.login.assert_called_once_with('synthetic', PASSWORD, verification_code='')
        client._send_private_request.assert_called_once_with('accounts/current_user/',
            params={'edit': 'true'}, headers={'Authorization': 'synthetic-authorization'})
        self.assertTrue(report['session_verified'])
        self.assertFalse(report['two_factor_requested'])
        self.assertNotIn(PAYLOAD, json.dumps(report))
        self.assertEqual(settings['cookies']['sessionid'], PAYLOAD)
        read_code.assert_not_called()

    def test_partial_identity_and_malformed_current_user_are_never_verified(self):
        for response in ({'user': {'pk': 999}}, {}, [], {'user': None}):
            client = self.client()
            client._send_private_request.return_value = response
            report = {}
            with self.assertRaises(CatalogFailure) as failure:
                login_interactively(client, 'synthetic', PASSWORD, report)
            self.assertEqual(failure.exception.code, 'INSTAGRAM_SESSION_UNVERIFIED')
            self.assertFalse(report['session_verified'])
            client.get_settings.assert_not_called()

    def test_client_rejection_exports_phase_and_status_without_prompting_or_retrying(self):
        class ClientNeedsUpgradeError(Exception):
            response = SimpleNamespace(status_code=400)
        client = self.client()
        client.user_id = None
        client._send_private_request.side_effect = ClientNeedsUpgradeError(PAYLOAD)
        client.login.side_effect = lambda *a, **k: client.private_request('accounts/login/', data={'password': PASSWORD})
        read_code = Mock()
        report = {}
        with self.assertRaises(ClientNeedsUpgradeError):
            login_interactively(client, 'synthetic', PASSWORD, report, read_code=read_code)
        self.assertEqual(report['login_request_phase'], 'legacy_password')
        self.assertEqual(report['provider_http_status'], 400)
        self.assertEqual(client._send_private_request.call_count, 1)
        self.assertNotIn(PAYLOAD, json.dumps(report))
        self.assertNotIn(PASSWORD, json.dumps(report))
        read_code.assert_not_called()

    def test_timeout_uses_only_one_transport_request_and_restores_original_helper(self):
        class ClientRequestTimeout(Exception):
            pass
        client = self.client()
        original = client.private_request
        client._send_private_request.side_effect = ClientRequestTimeout(PAYLOAD)
        with self.assertRaises(ClientRequestTimeout), single_attempt_requests(client, {}):
            client.private_request('accounts/login/')
        self.assertIs(client.private_request, original)
        self.assertEqual(client._send_private_request.call_count, 1)
        original.assert_not_called()

    def test_sdk_rethrow_of_an_earlier_failure_keeps_that_requests_phase(self):
        class ClientNeedsUpgradeError(Exception):
            response = SimpleNamespace(status_code=400)
        client = self.client()
        original_error = ClientNeedsUpgradeError(PAYLOAD)
        client._send_private_request.side_effect = [original_error, {}]
        def login(*args, **kwargs):
            try:
                client.private_request('accounts/login/')
            except ClientNeedsUpgradeError as saved:
                client.private_request('unknown/temporary-preflight/')
                raise saved
        client.login.side_effect = login
        report = {}
        with self.assertRaises(ClientNeedsUpgradeError):
            login_interactively(client, 'synthetic', PASSWORD, report)
        self.assertEqual(report['login_request_phases'], ['legacy_password', 'other_login_request'])
        self.assertEqual(report['login_request_phase'], 'legacy_password')
        self.assertEqual(report['provider_http_status'], 400)
        self.assertNotIn('unknown/temporary-preflight/', json.dumps(report))

    def test_repeated_password_and_unbounded_requests_stop_before_network(self):
        client = self.client()
        report = {}
        with self.assertRaises(CatalogFailure) as failure, single_attempt_requests(client, report):
            client.private_request('accounts/login/')
            client.private_request('accounts/login/')
        self.assertEqual(failure.exception.code, 'INSTAGRAM_LOGIN_REPEAT_BLOCKED')
        self.assertEqual(client._send_private_request.call_count, 1)
        client = self.client()
        report = {}
        with self.assertRaises(CatalogFailure) as failure, single_attempt_requests(client, report):
            for _ in range(41):
                client.private_request(PAYLOAD, data={'private': PASSWORD})
        self.assertEqual(failure.exception.code, 'INSTAGRAM_LOGIN_REQUEST_LIMIT')
        self.assertEqual(client._send_private_request.call_count, 40)
        self.assertNotIn(PAYLOAD, json.dumps(report))

    def test_blocked_sdk_loop_preserves_original_legacy_error_and_http_status(self):
        class ClientNeedsUpgradeError(Exception):
            response = SimpleNamespace(status_code=400)
        client = self.client()
        original_error = ClientNeedsUpgradeError(PAYLOAD)
        client._send_private_request.side_effect = [{}, original_error]
        report = {}
        with self.assertRaises(ClientNeedsUpgradeError) as failure, single_attempt_requests(client, report):
            client.private_request('bloks/async_action/com.bloks.www.bloks.caa.login.async.send_login_request/')
            try:
                client.private_request('accounts/login/')
            except ClientNeedsUpgradeError:
                client.private_request('bloks/async_action/com.bloks.www.bloks.caa.login.async.send_login_request/')
        self.assertIs(failure.exception, original_error)
        self.assertEqual(client._send_private_request.call_count, 2)
        self.assertTrue(report['login_repeat_blocked'])
        self.assertEqual(report['login_request_phase'], 'legacy_password')
        self.assertEqual(report['provider_http_status'], 400)

    def test_device_registration_failure_is_classified_without_graphql_payloads(self):
        class ClientError(Exception):
            response = SimpleNamespace(status_code=403)
        client = self.client()
        original = Mock(side_effect=ClientError(PAYLOAD))
        client.private_graphql_www_request = original
        report = {}
        with self.assertRaises(ClientError), single_attempt_requests(client, report):
            client.private_graphql_www_request('IGUSDIDRegistrationMutation', {'private': PAYLOAD})
        self.assertEqual(report['login_request_phase'], 'device_registration')
        self.assertEqual(report['provider_http_status'], 403)
        self.assertIs(client.private_graphql_www_request, original)
        self.assertNotIn(PAYLOAD, json.dumps(report))

    def test_checkpoint_never_prompts_for_two_factor_or_invokes_sdk_console_handler(self):
        class ChallengeRequired(Exception):
            pass
        client = self.client()
        original = Mock(side_effect=AssertionError('No checkpoint console handler'))
        client.challenge_code_handler = original
        def login(*args, **kwargs):
            self.assertEqual(client.challenge_code_handler('synthetic', 'sms'), '')
            raise ChallengeRequired(PAYLOAD)
        client.login.side_effect = login
        read_code = Mock()
        with self.assertRaises(ChallengeRequired):
            login_interactively(client, 'synthetic', PASSWORD, {}, read_code=read_code)
        read_code.assert_not_called(); original.assert_not_called()
        self.assertIs(client.challenge_code_handler, original)

    def test_two_factor_without_continuation_never_restarts_password_login(self):
        class TwoFactorRequired(Exception):
            pass
        client = self.client()
        client.user_id = None
        client.login.side_effect = TwoFactorRequired(PAYLOAD)
        client._extract_two_step_verification_context = Mock(return_value='')
        report = {}
        read_code = Mock()
        with self.assertRaises(CatalogFailure) as failure:
            login_interactively(client, 'synthetic', PASSWORD, report, read_code=read_code)
        self.assertEqual(failure.exception.code, 'INSTAGRAM_TWO_FACTOR_UNSUPPORTED')
        self.assertTrue(report['two_factor_requested'])
        self.assertFalse(report['two_factor_code_submitted'])
        self.assertEqual(client.login.call_count, 1)
        read_code.assert_not_called()


class InstalledSdkTests(unittest.TestCase):
    def run_challenge(self, *, code=CODE, sms=True, totp=False, choice='sms', verify_user=123):
        client = make_instagram_client()
        report, operations = {}, []
        initial = {'logged_in': False, 'two_step_verification_context': CONTEXT,
                   'sms_two_factor_on': sms, 'totp_two_factor_on': totp}
        client.bloks_caa_login = Mock(return_value=initial)
        original_login = client.login
        client.login = Mock(wraps=original_login)
        def send(endpoint, *args, **kwargs):
            operations.append(endpoint)
            print(PAYLOAD)  # Simulated SDK output must stay suppressed.
            if endpoint.endswith('verify_code.async/'):
                params = json.loads(kwargs['data']['params'])
                self.assertEqual(params['client_input_params']['code'], code)
                self.assertEqual(params['server_params']['challenge'], 'sms' if sms and not totp else choice)
                return {'cookies': {'sessionid': PAYLOAD, 'ds_user_id': '123'}}
            if endpoint == 'accounts/current_user/':
                return {'user': {'pk': verify_user}}
            return {}
        client._send_private_request = Mock(side_effect=send)
        def read_code(prompt):
            # The real SDK method-selection request already happened. No old
            # SMS is requested before the initial password submission/challenge.
            self.assertTrue(operations[-1].endswith('method_picker.navigation.async/'))
            operations.append('hidden_prompt')
            return code
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                try:
                    settings = login_interactively(client, 'synthetic', PASSWORD, report,
                        read_code=read_code, choose_method=lambda prompt: choice)
                    result = None
                except CatalogFailure as error:
                    settings, result = None, error.code
            self.assertEqual(client.login.call_count, 1)
            self.assertNotIn(PAYLOAD, output.getvalue() + json.dumps(report))
            self.assertNotIn(CONTEXT, json.dumps(report))
            self.assertNotIn(CODE, output.getvalue() + json.dumps(report))
            return report, operations, settings, result
        finally:
            InstagramReelsProvider(client).close()

    def test_real_sdk_sms_challenge_selects_delivery_then_prompts_then_verifies_session(self):
        report, operations, settings, result = self.run_challenge()
        self.assertIsNone(result)
        self.assertTrue(report['session_verified'])
        self.assertTrue(report['two_factor_requested'])
        self.assertTrue(report['two_factor_code_submitted'])
        self.assertEqual(report['two_factor_method'], 'sms')
        self.assertEqual(report['login_request_phase'], 'verify_session')
        self.assertEqual(operations[-1], 'accounts/current_user/')
        self.assertEqual(settings['cookies']['sessionid'], PAYLOAD)

    def test_real_sdk_authenticator_method_is_explicit_and_supported(self):
        report, _, _, result = self.run_challenge(sms=False, totp=True, choice='totp')
        self.assertIsNone(result)
        self.assertEqual(report['two_factor_method'], 'totp')

    def test_missing_or_malformed_code_does_not_submit_or_repeat_login(self):
        for code, expected in (('', 'INSTAGRAM_TWO_FACTOR_CANCELLED'),
                               ('malformed', 'INSTAGRAM_TWO_FACTOR_INVALID_INPUT')):
            report, operations, settings, result = self.run_challenge(code=code)
            self.assertEqual(result, expected)
            self.assertFalse(report['two_factor_code_submitted'])
            self.assertFalse(any(endpoint.endswith('verify_code.async/') for endpoint in operations))
            self.assertIsNone(settings)

    def test_unknown_method_can_cancel_without_requesting_sms_or_submitting_code(self):
        report, operations, _, result = self.run_challenge(sms=False, totp=False, choice='')
        self.assertEqual(result, 'INSTAGRAM_TWO_FACTOR_CANCELLED')
        self.assertEqual(operations, [])
        self.assertFalse(report['two_factor_code_submitted'])

    def test_verified_code_without_matching_session_is_not_ready(self):
        report, _, settings, result = self.run_challenge(verify_user=999)
        self.assertEqual(result, 'INSTAGRAM_SESSION_UNVERIFIED')
        self.assertFalse(report['session_verified'])
        self.assertIsNone(settings)

    def test_device_registration_key_survives_private_profile_without_account_auth(self):
        first = make_instagram_client()
        second = None
        try:
            first.usdid_generate()
            first.usdid_registered = True
            settings = first.get_settings()
            settings['usdid']['untrusted_extra'] = PAYLOAD
            settings['cookies']['sessionid'] = PAYLOAD
            pending = device_settings(settings)
            self.assertNotIn(PAYLOAD, json.dumps(pending))
            second = make_instagram_client(pending)
            self.assertEqual(first.usdid_private_key, second.usdid_private_key)
            self.assertEqual(first.usdid, second.usdid)
            self.assertTrue(second.usdid_registered)
            self.assertIsNone(second.user_id)
            self.assertEqual(second.authorization_data, {})
        finally:
            InstagramReelsProvider(first).close()
            if second is not None:
                InstagramReelsProvider(second).close()


class BrowserSessionTests(unittest.TestCase):
    session_id = '123%3ASYNTHETIC_BROWSER_SESSION_NEVER_EXPORT'

    def test_real_sdk_session_connection_verifies_user_and_never_logs_in_with_password(self):
        client = make_instagram_client()
        client.login = Mock(side_effect=AssertionError('No password login'))
        client.user_info_v1 = Mock(return_value=SimpleNamespace(pk=123, username='synthetic'))
        client._send_private_request = Mock(return_value={'user': {'pk': 123, 'username': 'synthetic'}})
        report = {}
        try:
            settings = login_with_browser_session(client, 'SYNTHETIC', self.session_id, report)
            self.assertTrue(report['session_verified'])
            self.assertEqual(report['connection_method'], 'browser_session')
            self.assertFalse(report['two_factor_requested'])
            self.assertEqual(settings['cookies']['sessionid'], self.session_id)
            client.login.assert_not_called()
            client._send_private_request.assert_called_once()
            self.assertNotIn(self.session_id, json.dumps(report))
        finally:
            InstagramReelsProvider(client).close()

    def test_browser_account_mismatch_is_not_a_verified_connection(self):
        client = SimpleNamespace(user_id=123, authorization='',
            login_by_sessionid=Mock(return_value=True),
            _send_private_request=Mock(return_value={'user': {'pk': 123, 'username': 'another_account'}}),
            get_settings=Mock())
        report = {}
        with self.assertRaises(CatalogFailure) as failure:
            login_with_browser_session(client, 'synthetic', self.session_id, report)
        self.assertEqual(failure.exception.code, 'INSTAGRAM_SESSION_ACCOUNT_MISMATCH')
        self.assertFalse(report['session_verified'])
        client.get_settings.assert_not_called()

    def test_invalid_cookie_input_never_reaches_sdk_and_never_appears_in_error(self):
        for value in ('', 'not-a-valid-session', '123 ' + PAYLOAD, PAYLOAD * 1000):
            client = SimpleNamespace(login_by_sessionid=Mock())
            with self.assertRaises(CatalogFailure) as failure:
                login_with_browser_session(client, 'synthetic', value, {})
            self.assertEqual(failure.exception.code, 'INSTAGRAM_SESSION_INPUT_INVALID')
            self.assertNotIn(PAYLOAD, str(failure.exception))
            client.login_by_sessionid.assert_not_called()

    def test_browser_path_refuses_any_password_request_before_network(self):
        client = SimpleNamespace(user_id=None, authorization='', _send_private_request=Mock())
        client.login_by_sessionid = lambda session_id: client.private_request('accounts/login/')
        with self.assertRaises(CatalogFailure) as failure:
            login_with_browser_session(client, 'synthetic', self.session_id, {})
        self.assertEqual(failure.exception.code, 'INSTAGRAM_UNEXPECTED_PASSWORD_REQUEST')
        client._send_private_request.assert_not_called()
