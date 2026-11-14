"""Local, single-attempt login with challenge-timed hidden 2FA input."""
from __future__ import annotations

from contextlib import contextmanager
import getpass
import re

from .instagram import quiet_instagram
from .service import CatalogFailure


REQUEST_PHASES = {
    'accounts/login/': 'legacy_password',
    'accounts/two_factor_login/': 'legacy_two_factor',
    'accounts/current_user/': 'verify_session',
    'launcher/sync/': 'launcher_sync',
    'attestation/create_android_keystore/': 'device_attestation',
    'bloks/async_action/com.bloks.www.bloks.caa.login.process_client_data_and_redirect/': 'caa_prepare',
    'bloks/async_action/com.bloks.www.caa.login.oauth.token.fetch.async/': 'caa_token_prepare',
    'bloks/async_action/com.bloks.www.bloks.caa.login.async.send_login_request/': 'caa_password',
    'bloks/apps/com.bloks.www.two_step_verification.entrypoint/': 'two_factor_entry',
    'bloks/apps/com.bloks.www.two_step_verification.method_picker/': 'two_factor_methods',
    'bloks/async_action/com.bloks.www.two_step_verification.method_picker.navigation.async/': 'two_factor_select',
    'bloks/async_action/com.bloks.www.two_step_verification.verify_code.async/': 'two_factor_verify',
}
SAFE_PHASES = set(REQUEST_PHASES.values()) | {'device_registration', 'other_login_request'}


@contextmanager
def single_attempt_requests(client, report, *, allow_password=True):
    """Avoid SDK timeout/login loops; export fixed phases, never URLs or bodies."""
    previous = client.__dict__.get('private_request')
    previous_challenge = client.__dict__.get('challenge_code_handler')
    previous_graphql = client.__dict__.get('private_graphql_www_request')
    graphql = getattr(client, 'private_graphql_www_request', None)
    password_phases = set()
    password_failure = None
    report['login_request_phases'] = []
    report['login_request_count'] = 0

    def tracked(phase, function, *args, **kwargs):
        nonlocal password_failure
        report['login_request_phase'] = phase
        if report['login_request_count'] >= 40:
            raise CatalogFailure(409, 'INSTAGRAM_LOGIN_REQUEST_LIMIT', 'Login stopped at its request limit. Review Instagram locally.')
        if phase in {'caa_password', 'legacy_password'}:
            if not allow_password:
                raise CatalogFailure(409, 'INSTAGRAM_UNEXPECTED_PASSWORD_REQUEST', 'Session connection stopped before an unexpected password request.')
            if phase in password_phases:
                report['login_repeat_blocked'] = True
                if password_failure is not None:
                    raise password_failure
                raise CatalogFailure(409, 'INSTAGRAM_LOGIN_REPEAT_BLOCKED', 'The SDK requested a repeated password submission. No retry was sent.')
            password_phases.add(phase)
        report['login_request_count'] += 1
        report['login_request_phases'].append(phase)
        try:
            return function(*args, **kwargs)
        except Exception as error:
            # The SDK may retain/rethrow an earlier error after a fallback. Tag
            # that exception in memory so the final diagnostic names its phase.
            error._adi_login_phase = phase
            status = getattr(getattr(error, 'response', None), 'status_code', None)
            if type(status) is int and 100 <= status <= 599:
                error._adi_login_http_status = status
            if phase in {'caa_password', 'legacy_password'}:
                password_failure = error
            raise

    def request(endpoint, *args, **kwargs):
        headers = dict(kwargs.pop('headers', None) or {})
        authorization = getattr(client, 'authorization', '')
        if authorization and not any(key.lower() == 'authorization' for key in headers):
            headers['Authorization'] = authorization
        return tracked(REQUEST_PHASES.get(endpoint, 'other_login_request'),
                       client._send_private_request, endpoint, *args, headers=headers, **kwargs)

    if graphql is not None:
        def graphql_request(friendly_name, *args, **kwargs):
            phase = 'device_registration' if friendly_name == 'IGUSDIDRegistrationMutation' else 'other_login_request'
            return tracked(phase, graphql, friendly_name, *args, **kwargs)
        client.private_graphql_www_request = graphql_request
    client.private_request = request
    # CAA profile/contact verification is a checkpoint, not account 2FA. Leave
    # it to the official app rather than invoking an SDK console handler/loop.
    client.challenge_code_handler = lambda *_args, **_kwargs: ''
    try:
        yield
    except Exception as error:
        phase = getattr(error, '_adi_login_phase', None)
        if phase in SAFE_PHASES:
            report['login_request_phase'] = phase
        status = getattr(error, '_adi_login_http_status', None)
        if type(status) is int and 100 <= status <= 599:
            report['provider_http_status'] = status
        raise
    finally:
        for name, value in (('private_request', previous), ('challenge_code_handler', previous_challenge),
                            ('private_graphql_www_request', previous_graphql)):
            if value is None:
                client.__dict__.pop(name, None)
            else:
                setattr(client, name, value)


def _call(function, *args, **kwargs):
    with quiet_instagram():
        return function(*args, **kwargs)


def _complete_two_factor(client, error, report, read_code, choose_method):
    report['two_factor_requested'] = True
    # Use the current server-issued context, never start a second password login.
    sources = [vars(error), getattr(client, 'last_json', {})]
    context, source = '', {}
    for candidate in sources:
        if isinstance(candidate, dict):
            context = _call(client._extract_two_step_verification_context, candidate)
            if context:
                source = candidate
                break
    if not context:
        raise CatalogFailure(409, 'INSTAGRAM_TWO_FACTOR_UNSUPPORTED',
                             'Instagram requested 2FA without a supported continuation. Review the account in the official app; no new login was sent.')
    sms = _call(client._login_response_bool, source, 'sms_two_factor_on')
    totp = _call(client._login_response_bool, source, 'totp_two_factor_on')
    if sms != totp:
        method = 'sms' if sms else 'totp'
    else:
        choice = choose_method('Instagram requested 2FA. Choose sms or totp (authenticator); Enter cancels: ').strip().lower()
        if choice not in {'sms', 'totp'}:
            raise CatalogFailure(409, 'INSTAGRAM_TWO_FACTOR_CANCELLED', 'No verification method selected. No code was submitted.')
        method = choice
    report['two_factor_method'] = method
    _call(client.bloks_two_step_verification_entrypoint, context)
    _call(client.bloks_two_step_verification_method_picker, context)
    # Method selection requests delivery before the SMS prompt. No resend loop.
    _call(client.bloks_two_step_verification_select_method, context, selected_method=method)
    label = 'new SMS code for this attempt' if method == 'sms' else 'current authenticator code'
    code = read_code(f'Enter the {label} (hidden; Enter cancels): ').strip()
    try:
        if not code:
            raise CatalogFailure(409, 'INSTAGRAM_TWO_FACTOR_CANCELLED', 'No code entered. No code was submitted.')
        if not re.fullmatch(r'[0-9]{6}', code):
            raise CatalogFailure(409, 'INSTAGRAM_TWO_FACTOR_INVALID_INPUT', 'Enter a six-digit code at the local prompt. No code was submitted.')
        report['two_factor_code_submitted'] = True
        result = _call(client.bloks_two_step_verification_verify_code, context, code, challenge=method)
        if not _call(client.bloks_apply_login_response, result) or not client.user_id:
            raise CatalogFailure(409, 'INSTAGRAM_TWO_FACTOR_REJECTED', 'Instagram did not return a session after verification. Review the account locally.')
    finally:
        code = ''
    return True


def _verified_settings(client, report, expected_username=None):
    report['stage'] = 'verify_instagram_session'
    # A cookie/ID or partial login is insufficient. Verify the canonical identity.
    response = _call(client.private_request, 'accounts/current_user/', params={'edit': 'true'})
    user = response.get('user') if isinstance(response, dict) else None
    identifier = user.get('pk') if isinstance(user, dict) else None
    if identifier is None or str(identifier) != str(client.user_id):
        raise CatalogFailure(409, 'INSTAGRAM_SESSION_UNVERIFIED', 'Instagram could not verify the new session. No ready connection was saved.')
    if expected_username is not None:
        name = user.get('username')
        if not isinstance(name, str) or name.casefold() != expected_username.strip().casefold():
            raise CatalogFailure(409, 'INSTAGRAM_SESSION_ACCOUNT_MISMATCH', 'This browser session does not match the Instagram username entered locally.')
    report['session_verified'] = True
    return _call(client.get_settings)


def login_interactively(client, username, password, report, *, read_code=None, choose_method=None):
    """One SDK login; only a returned account-2FA challenge may prompt for a code."""
    report.update(connection_method='password', two_factor_requested=False,
                  two_factor_code_submitted=False, session_verified=False)
    with single_attempt_requests(client, report):
        try:
            accepted = _call(client.login, username, password, verification_code='')
        except Exception as error:
            if type(error).__name__ != 'TwoFactorRequired':
                raise
            accepted = _complete_two_factor(client, error, report,
                                            read_code or getpass.getpass, choose_method or input)
        if not accepted or not client.user_id:
            raise CatalogFailure(409, 'INSTAGRAM_LOGIN_REJECTED', 'Instagram did not return an authenticated session. Review the account locally.')
        return _verified_settings(client, report)


def login_with_browser_session(client, username, session_id, report):
    """Restore an explicitly supplied local session through the SDK, without passwords."""
    report.update(connection_method='browser_session', two_factor_requested=False,
                  two_factor_code_submitted=False, session_verified=False)
    if not isinstance(session_id, str) or not 31 <= len(session_id) <= 16384 or not re.match(r'^\d+', session_id) or any(char.isspace() for char in session_id):
        raise CatalogFailure(409, 'INSTAGRAM_SESSION_INPUT_INVALID', 'Copy only the sessionid cookie value from your own signed-in Instagram browser.')
    with single_attempt_requests(client, report, allow_password=False):
        accepted = _call(client.login_by_sessionid, session_id)
        if not accepted or not client.user_id:
            raise CatalogFailure(409, 'INSTAGRAM_SESSION_UNVERIFIED', 'Instagram rejected this browser session for API use. No ready connection was saved.')
        return _verified_settings(client, report, expected_username=username)
