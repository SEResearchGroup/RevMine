from cryptography.fernet import Fernet

# Générer une clé
key = Fernet.generate_key()
print(f"ENCRYPTION_KEY={key.decode()}")
print("\nAjoutez cette ligne dans votre .env")