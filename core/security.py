"""Security utilities for encryption/decryption"""
import os
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional

_cipher_instance: Optional[Fernet] = None

def get_cipher() -> Fernet:
    """Get the Fernet cipher instance for encryption/decryption"""
    global _cipher_instance
    
    if _cipher_instance is not None:
        return _cipher_instance
    
    # Try to load from environment variable first
    key = os.getenv("MASTER_KEY")
    if key:
        _cipher_instance = Fernet(key.encode())
        return _cipher_instance
    
    # Try to load from file
    config_dir_env = os.environ.get('SOULSYNC_CONFIG_DIR')
    if config_dir_env:
        config_dir = Path(config_dir_env)
    else:
        config_dir = Path(__file__).parent.parent / 'config'
    
    key_path = config_dir / ".encryption_key"
    
    if key_path.exists():
        with open(key_path, 'rb') as f:
            key_bytes = f.read()
        _cipher_instance = Fernet(key_bytes)
        return _cipher_instance
    
    # Generate new key if none exists
    key_bytes = Fernet.generate_key()
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(key_path, 'wb') as f:
        f.write(key_bytes)
    key_path.chmod(0o600)
    
    _cipher_instance = Fernet(key_bytes)
    return _cipher_instance

def encrypt_string(plaintext: str) -> str:
    """Encrypt a string and return the encrypted payload prefixed with 'enc:'."""
    if plaintext is None:
        return None
    if str(plaintext).startswith('enc:'):
        return plaintext
    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(str(plaintext).encode('utf-8'))
    return f"enc:{encrypted_bytes.decode('utf-8')}"

def decrypt_string(ciphertext: str) -> str:
    """Decrypt a string if it is prefixed with 'enc:', otherwise return as-is."""
    if ciphertext is None:
        return None
    if not str(ciphertext).startswith('enc:'):
        return ciphertext
    cipher = get_cipher()
    try:
        decrypted_bytes = cipher.decrypt(ciphertext[4:].encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception:
        # Fallback to returning original string on decryption failure
        return ciphertext
