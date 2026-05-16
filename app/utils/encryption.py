import base64
import os
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

# Clave maestra leída una sola vez al importar
_KEY: bytes = base64.b64decode(settings.BIOMETRIC_KEY)
_aesgcm = AESGCM(_KEY)


def encrypt_bpm(bpm: float) -> tuple[str, str]:
    """
    Cifra un valor BPM con AES-256-GCM.
    Nonce aleatorio de 96 bits (12 bytes) por llamada — nunca se reusa.
    Devuelve (ciphertext_b64, nonce_b64).
    """
    nonce = os.urandom(12)
    plaintext = struct.pack(">d", bpm)  # 8 bytes big-endian double
    ciphertext = _aesgcm.encrypt(nonce, plaintext, None)
    return base64.b64encode(ciphertext).decode(), base64.b64encode(nonce).decode()


def decrypt_bpm(ciphertext_b64: str, nonce_b64: str) -> float:
    """
    Descifra y devuelve el BPM.
    Lanza cryptography.exceptions.InvalidTag si el ciphertext fue alterado (AEAD detecta tampering).
    """
    ciphertext = base64.b64decode(ciphertext_b64)
    nonce = base64.b64decode(nonce_b64)
    plaintext = _aesgcm.decrypt(nonce, ciphertext, None)
    return struct.unpack(">d", plaintext)[0]
