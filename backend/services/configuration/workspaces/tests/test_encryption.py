"""Unit tests for the infrastructure encryption provider and domain security service."""
import pytest
from unittest.mock import MagicMock, patch

from workspaces.infrastructure.security.encryption_provider import FernetEncryptionProvider
from workspaces.domain.security.encryption_service import TokenSecurityService


# ---------------------------------------------------------------------------
# FernetEncryptionProvider (infrastructure)
# ---------------------------------------------------------------------------

class TestFernetEncryptionProvider:
    """Tests for the low-level Fernet encryption provider."""

    @pytest.fixture
    def provider(self, settings):
        """Create a provider using a valid test key."""
        from cryptography.fernet import Fernet
        settings.ENCRYPTION_KEY = Fernet.generate_key().decode()
        return FernetEncryptionProvider()

    def test_encrypt_returns_non_empty_string(self, provider):
        encrypted = provider.encrypt("my_secret_token")
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_encrypt_does_not_return_plaintext(self, provider):
        token = "my_secret_token"
        encrypted = provider.encrypt(token)
        assert token not in encrypted

    def test_decrypt_roundtrip(self, provider):
        token = "ghp_testtoken12345"
        assert provider.decrypt(provider.encrypt(token)) == token

    def test_different_plaintexts_produce_different_ciphertexts(self, provider):
        enc1 = provider.encrypt("token_a")
        enc2 = provider.encrypt("token_b")
        assert enc1 != enc2

    def test_decrypt_invalid_data_raises(self, provider):
        with pytest.raises(Exception):
            provider.decrypt("not-valid-base64-fernet-data==")


# ---------------------------------------------------------------------------
# TokenSecurityService (domain)
# ---------------------------------------------------------------------------

class TestTokenSecurityService:
    """Tests for the domain-level token security service."""

    @pytest.fixture(autouse=True)
    def _patch_encryption(self):
        """Patch the module-level singleton so tests don't need real Fernet keys."""
        self.mock_provider = MagicMock()
        self.mock_provider.encrypt.side_effect = lambda t: f"enc:{t}"
        self.mock_provider.decrypt.side_effect = lambda t: t.removeprefix("enc:")
        with patch(
            "workspaces.domain.security.encryption_service.token_encryption",
            self.mock_provider,
        ):
            yield

    def test_secure_token_calls_encrypt(self):
        result = TokenSecurityService.secure_token("raw_token")
        self.mock_provider.encrypt.assert_called_once_with("raw_token")
        assert result == "enc:raw_token"

    def test_secure_token_raises_on_empty_token(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            TokenSecurityService.secure_token("")

    def test_retrieve_token_calls_decrypt(self):
        result = TokenSecurityService.retrieve_token("enc:raw_token")
        self.mock_provider.decrypt.assert_called_once_with("enc:raw_token")
        assert result == "raw_token"

    def test_roundtrip(self):
        secured = TokenSecurityService.secure_token("my_pat")
        retrieved = TokenSecurityService.retrieve_token(secured)
        assert retrieved == "my_pat"
