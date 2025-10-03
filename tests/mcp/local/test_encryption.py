from jotsu.mcp.local.encryption import Encryption


def test_encryption():
    key = '01234567890123456789012345678901'
    encryption = Encryption(key=key)

    plaintext = '123'
    ciphertext = encryption.encrypt(plaintext)
    assert encryption.decrypt(ciphertext) == plaintext
