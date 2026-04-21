def sign_bytes(key: bytes, message: bytes) -> bytes:
    """Pretend to sign; fixture only."""
    return key + message
