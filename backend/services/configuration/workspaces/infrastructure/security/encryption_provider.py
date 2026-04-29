"""Fernet-based token encryption provider.

Infrastructure layer: low-level implementation of symmetric encryption
using the ``cryptography`` library.  The domain layer calls this module
but never knows *which* algorithm is being used.
"""
from cryptography.fernet import Fernet
from django.conf import settings
import base64


class FernetEncryptionProvider:
    """Implements token encryption with Fernet (AES-128-CBC + HMAC-SHA256)."""

    def __init__(self):
        key = settings.ENCRYPTION_KEY.encode()
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt *plaintext* and return a base64-encoded ciphertext string."""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded *ciphertext* and return the plaintext."""
        encrypted = base64.b64decode(ciphertext.encode())
        return self.cipher.decrypt(encrypted).decode()


# Module-level singleton — avoids re-initialising the cipher on every call.
token_encryption = FernetEncryptionProvider()
