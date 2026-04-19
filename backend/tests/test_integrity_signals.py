"""Hash vs signature cues for evidence claims."""

from analysis.integrity_signals import infer_integrity_fields


def test_hash_only_not_signed() -> None:
    r = infer_integrity_fields(
        "The bundle content hash is sha256:deadbeef… for integrity checking."
    )
    assert r["integrity_status"] == "hashed_only"
    assert r["content_hash_present"] is True
    assert r["signature_present"] is False


def test_signature_is_signed() -> None:
    r = infer_integrity_fields(
        "Payload includes a cryptographic signature using Ed25519 and a public key for verification."
    )
    assert r["integrity_status"] == "signed"
    assert r["signature_present"] is True
    assert r["public_key_present"] is True


def test_hex64_with_hash_context_is_hashed_only() -> None:
    claim = "Record fingerprint sha " + "a" * 64 + " stored in manifest."
    r = infer_integrity_fields(claim)
    assert r["integrity_status"] == "hashed_only"
    assert r["content_hash_present"] is True


def test_plain_claim_unsigned() -> None:
    r = infer_integrity_fields("This module handles user preferences.")
    assert r["integrity_status"] == "unsigned"
    assert r["content_hash_present"] is False
    assert r["signature_present"] is False


def test_signed_overrides_hash_in_status() -> None:
    r = infer_integrity_fields(
        "Signed payload with sha256 digest abc… and Ed25519 signature block."
    )
    assert r["integrity_status"] == "signed"
