# SHIM: content moved to workspaces.infrastructure.security.encryption_provider
# re-exported for backward compatibility (models.py imports token_encryption from here).
from workspaces.infrastructure.security.encryption_provider import (
    FernetEncryptionProvider as TokenEncryption,
    token_encryption,
)

__all__ = ["TokenEncryption", "token_encryption"]
