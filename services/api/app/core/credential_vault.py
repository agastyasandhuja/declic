"""Authenticated encryption; the key stays outside Atlas and all client bundles."""

import base64
import json
import secrets

from Cryptodome.Cipher import AES


class CredentialVault:
    def __init__(self, encoded_key: str):
        try:
            self.key = base64.b64decode(encoded_key, validate=True)
        except ValueError:
            raise ValueError("CONNECTION_ENCRYPTION_KEY must be base64") from None
        if len(self.key) != 32:
            raise ValueError("CONNECTION_ENCRYPTION_KEY must encode 32 random bytes")

    def seal(self, owner: str, provider: str, value: dict) -> str:
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=secrets.token_bytes(12))
        cipher.update(json.dumps([owner, provider]).encode())
        ciphertext, tag = cipher.encrypt_and_digest(json.dumps(value).encode())
        return base64.b64encode(cipher.nonce + tag + ciphertext).decode()

    def open(self, owner: str, provider: str, value: str) -> dict:
        raw = base64.b64decode(value, validate=True)
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=raw[:12])
        cipher.update(json.dumps([owner, provider]).encode())
        return json.loads(cipher.decrypt_and_verify(raw[28:], raw[12:28]))
