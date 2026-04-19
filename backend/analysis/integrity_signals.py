"""Heuristic hash vs signature cues for evidence claims — avoids implying signing from a bare hash."""

from __future__ import annotations

import re

# Signature / signing semantics (conservative: avoid matching "assignment", etc.)
_SIG_RE = re.compile(
    r"cryptographic\s+signature|digital\s+signature|"
    r"(?<![a-z])signature(?![a-z])|"
    r"\bed25519\b|\becdsa\b|rsa\s+signature|"
    r"verify_signature|verif(?:y|ication)\s+of\s+(?:the\s+)?signature|"
    r"signed\s+(?:payload|message|hash|document|content)|"
    r"includes\s+(?:a\s+)?(?:cryptographic\s+)?signature|"
    r"\bsigning\s+key\b|signature\s+verification",
    re.IGNORECASE,
)

# Public / private key material mentioned alongside crypto
_KEY_RE = re.compile(
    r"public\s+key|public_key|\bpubkey\b|verifying\s+key|"
    r"private\s+key|secret\s+key\s+pair|key\s+pair",
    re.IGNORECASE,
)

# Content hashing / digests (not proof of signer identity by themselves)
_HASH_RE = re.compile(
    r"\bsha_?256\b|\bsha-256\b|\bsha256\s*:|"
    r"\bsha_?512\b|\bsha-1\b|\bmd5\b|"
    r"content\s+hash|message\s+digest|hash\s+of\s+(?:the\s+)?|"
    r"\bhex\s+digest\b|fingerprint\s+of|"
    r"\bchecksum\b",
    re.IGNORECASE,
)

# Standalone 64-char hex often used as SHA-256 display; require nearby hash language
_HEX64_RE = re.compile(r"\b[0-9a-f]{64}\b", re.IGNORECASE)
_HASH_CONTEXT_RE = re.compile(
    r"hash|digest|fingerprint|checksum|sha",
    re.IGNORECASE,
)


def _has_likely_hash(claim: str) -> bool:
    if _HASH_RE.search(claim):
        return True
    for m in _HEX64_RE.finditer(claim):
        start = max(0, m.start() - 48)
        end = min(len(claim), m.end() + 48)
        if _HASH_CONTEXT_RE.search(claim[start:end]):
            return True
    return False


def infer_integrity_fields(claim: str | None) -> dict:
    """
    Derive booleans + integrity_status for API/UX. Does not assert verification was run.
    """
    text = (claim or "").strip()
    if not text:
        return {
            "content_hash_present": False,
            "signature_present": False,
            "public_key_present": False,
            "integrity_status": "unsigned",
        }

    has_sig = bool(_SIG_RE.search(text))
    has_key = bool(_KEY_RE.search(text))
    has_hash = _has_likely_hash(text)

    if has_sig:
        status = "signed"
    elif has_hash:
        status = "hashed_only"
    else:
        status = "unsigned"

    return {
        "content_hash_present": bool(has_hash),
        "signature_present": bool(has_sig),
        "public_key_present": bool(has_key),
        "integrity_status": status,
    }
