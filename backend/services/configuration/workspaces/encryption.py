from cryptography.fernet import Fernet
from django.conf import settings
import base64

class TokenEncryption:
    def __init__(self):
        key = settings.ENCRYPTION_KEY.encode()
        self.cipher = Fernet(key)
    
    def encrypt(self, token: str) -> str:
        """Encrypting a token"""
        encrypted = self.cipher.encrypt(token.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_token: str) -> str:
        """Decrypting a token"""
        encrypted = base64.b64decode(encrypted_token.encode())
        return self.cipher.decrypt(encrypted).decode()

token_encryptor = TokenEncryption()