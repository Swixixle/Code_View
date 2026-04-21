from sweeps_relief_fixture.subpkg import sign_bytes


def consume(key: bytes, data: bytes) -> bytes:
    return sign_bytes(key, data)
