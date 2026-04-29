"""Domain-level token security service.

Defines *what* to encrypt and *when* — business semantics.
Delegates *how* to the infrastructure encryption provider.

The domain layer is intentionally thin here: it enforces that tokens are
never stored in plaintext and provides named operations (``secure_token``,
``retrieve_token``) that are meaningful to the business.
"""
from workspaces.infrastructure.security.encryption_provider import token_encryption


class TokenSecurityService:
    """Domain service for API token protection.

    All token persistence in the application MUST go through this service so
    that encryption details remain isolated in the infrastructure layer.
    """

    @staticmethod
    def secure_token(raw_token: str) -> str:
        """Encrypt a raw API token for secure storage.

        Args:
            raw_token: Plaintext API token (e.g. GitHub PAT, GitLab PAT)

        Returns:
            Encrypted token string safe for database persistence

        Raises:
            ValueError: If *raw_token* is empty
        """
        if not raw_token:
            raise ValueError("Token cannot be empty")
        return token_encryption.encrypt(raw_token)

    @staticmethod
    def retrieve_token(encrypted_token: str) -> str:
        """Decrypt a stored token for API use.

        Args:
            encrypted_token: Previously encrypted token from the database

        Returns:
            Decrypted plaintext token
        """
        return token_encryption.decrypt(encrypted_token)
