from sweeps_relief_fixture.signer import sign_bytes


def log_event(key: bytes, event: bytes) -> bytes:
    return sign_bytes(key, event)
