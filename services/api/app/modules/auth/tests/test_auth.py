import unittest
import httpx
from app.modules.auth.service import SupabaseVerifier, AuthFailure


class VerificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_configuration_never_receives_a_token(self):
        for url, key in (('http://auth.example.test', 'key'), ('https://secret@auth.example.test', 'key'), ('https://auth.example.test/path', 'key'), ('https://auth.example.test', '')):
            with self.assertRaises(ValueError):
                SupabaseVerifier(url, key)

    async def test_untrusted_metadata_and_malformed_auth_responses(self):
        for data in ({'id': '', 'created_at': '2026-11-14T00:00:00Z'}, {'id': 'valid', 'created_at': '2026-11-14T00:00:00'}, {'id': 'valid'}, []):
            verifier = SupabaseVerifier('https://auth.example.test', 'synthetic', httpx.MockTransport(lambda _: httpx.Response(200, json=data)))
            with self.assertRaises(AuthFailure) as raised:
                await verifier.verify_access_token('synthetic-token')
            self.assertEqual(raised.exception.status, 503)

    async def test_provider_auth_remains_the_source_of_the_subject(self):
        verifier = SupabaseVerifier('https://auth.example.test', 'synthetic', httpx.MockTransport(lambda _: httpx.Response(200, json={'id': 'verified-subject', 'email': None, 'created_at': '2026-11-14T00:00:00+00:00', 'user_metadata': {'user_id': 'forged', 'role': 'admin'}})))
        user = await verifier.verify_access_token('synthetic-token')
        self.assertEqual(user['user_id'], 'verified-subject')
        self.assertNotIn('role', user)
