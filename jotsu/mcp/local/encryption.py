import secrets

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAVE_CRYPTOGRAPHY = True
except ImportError:
    AESGCM = None
    HAVE_CRYPTOGRAPHY = False

if HAVE_CRYPTOGRAPHY:

    # https://stackoverflow.com/a/59835994
    class Encryption:

        def __init__(self, key: str):
            assert len(key) == 32
            self._aesgcm = AESGCM(key.encode())

        def encrypt(self, plaintext: str) -> bytes:
            nonce = secrets.token_bytes(12)  # GCM mode needs 12 fresh bytes every time
            return nonce + self._aesgcm.encrypt(nonce, plaintext.encode(), None)

        def decrypt(self, ciphertext: bytes) -> str:
            plaintext = self._aesgcm.decrypt(ciphertext[:12], ciphertext[12:], None)
            return plaintext.decode()
