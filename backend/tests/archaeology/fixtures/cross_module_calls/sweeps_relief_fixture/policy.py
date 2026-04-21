from .signer import sign_bytes


def build_policy(key: bytes, body: bytes) -> bytes:
    return sign_bytes(key, body)
