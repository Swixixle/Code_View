"""
Crypto- and security-aware documentation claim extraction.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List

from models.evidence import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    SourceLocation,
)

logger = logging.getLogger(__name__)


class EnhancedClaimsExtractor:
    """README / markdown claims with cryptographic and evidence-first patterns."""

    def __init__(self) -> None:
        self.capability_patterns = [
            r"supports?\s+([^.]+)",
            r"provides?\s+([^.]+)",
            r"implements?\s+([^.]+)",
            r"enables?\s+([^.]+)",
            r"can\s+([^.]+)",
            r"allows?\s+([^.]+)",
            r"signs?\s+([^.]+)",
            r"verifies?\s+([^.]+)",
            r"encrypts?\s+([^.]+)",
            r"hashes?\s+([^.]+)",
            r"generates?\s+([^.]+)",
            r"proves?\s+([^.]+)",
            r"attests?\s+([^.]+)",
            r"receipts?\s+([^.]+)",
        ]

        self.crypto_keywords = {
            "ed25519": {"weight": 10, "category": "signature"},
            "cryptographic": {"weight": 8, "category": "general_crypto"},
            "signature": {"weight": 8, "category": "signature"},
            "signing": {"weight": 8, "category": "signature"},
            "verification": {"weight": 8, "category": "verification"},
            "receipt": {"weight": 9, "category": "evidence"},
            "proof": {"weight": 8, "category": "evidence"},
            "attestation": {"weight": 7, "category": "evidence"},
            "hash": {"weight": 6, "category": "hashing"},
            "sha256": {"weight": 7, "category": "hashing"},
            "blake2": {"weight": 7, "category": "hashing"},
            "authentication": {"weight": 6, "category": "auth"},
            "authorization": {"weight": 6, "category": "auth"},
            "security": {"weight": 5, "category": "general_security"},
            "trust": {"weight": 6, "category": "trust"},
            "integrity": {"weight": 6, "category": "integrity"},
            "provenance": {"weight": 8, "category": "evidence"},
            "audit": {"weight": 7, "category": "evidence"},
            "tamper": {"weight": 7, "category": "integrity"},
            "immutable": {"weight": 6, "category": "integrity"},
        }

        self.evidence_keywords = [
            "evidence",
            "proof",
            "receipt",
            "attestation",
            "witness",
            "provenance",
            "audit",
            "trail",
            "chain",
            "verification",
            "signing",
            "signature",
            "cryptographic",
            "hash",
        ]

        self.credibility_keywords = [
            "institutional",
            "credibility",
            "trust",
            "verification",
            "transparency",
            "accountability",
            "auditable",
            "verifiable",
        ]

    def extract_claims_from_text(self, text: str, file_path: str) -> List[EvidenceItem]:
        lines = text.split("\n")
        claims: List[EvidenceItem] = []
        claims.extend(self._extract_capability_claims(lines, file_path))
        claims.extend(self._extract_crypto_claims(lines, file_path))
        claims.extend(self._extract_evidence_claims(lines, file_path))
        claims.extend(self._extract_credibility_claims(lines, file_path))
        claims.extend(self._extract_feature_claims(lines, file_path))
        return claims

    def _extract_capability_claims(self, lines: List[str], file_path: str) -> List[EvidenceItem]:
        claims: List[EvidenceItem] = []
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower().strip()
            if not line_lower or line.startswith("#"):
                continue
            for pattern in self.capability_patterns:
                match = re.search(pattern, line_lower)
                if match:
                    capability = match.group(1).strip()
                    confidence = self._assess_claim_confidence(capability)
                    claims.append(
                        EvidenceItem(
                            claim=f"System claims to {capability}",
                            status=EvidenceStatus.UNKNOWN,
                            evidence_type=EvidenceType.EXTRACTED,
                            confidence=confidence,
                            source_locations=[
                                SourceLocation(file_path=file_path, line_start=line_num)
                            ],
                            reasoning_chain=[f"Capability pattern in documentation: {line.strip()}"],
                            analysis_stage="enhanced_claims_extraction",
                        )
                    )
        return claims

    def _extract_crypto_claims(self, lines: List[str], file_path: str) -> List[EvidenceItem]:
        claims: List[EvidenceItem] = []
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower().strip()
            for keyword, info in self.crypto_keywords.items():
                if keyword in line_lower:
                    context = self._extract_keyword_context(line, keyword)
                    claims.append(
                        EvidenceItem(
                            claim=f"Cryptographic/security documentation: {context}",
                            status=EvidenceStatus.UNKNOWN,
                            evidence_type=EvidenceType.EXTRACTED,
                            confidence=ConfidenceLevel.HIGH
                            if info["weight"] >= 8
                            else ConfidenceLevel.MEDIUM,
                            source_locations=[
                                SourceLocation(file_path=file_path, line_start=line_num)
                            ],
                            reasoning_chain=[
                                f"Keyword category: {info['category']}",
                                line.strip(),
                            ],
                            analysis_stage="cryptographic_claims_extraction",
                            boundary_note=f"Trust boundary context: {info['category']}",
                        )
                    )
        return claims

    def _extract_evidence_claims(self, lines: List[str], file_path: str) -> List[EvidenceItem]:
        claims: List[EvidenceItem] = []
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            score = sum(1 for kw in self.evidence_keywords if kw in line_lower)
            if score >= 2:
                claims.append(
                    EvidenceItem(
                        claim=f"Evidence-first language (heuristic): {line.strip()}",
                        status=EvidenceStatus.UNKNOWN,
                        evidence_type=EvidenceType.EXTRACTED,
                        confidence=ConfidenceLevel.HIGH,
                        source_locations=[
                            SourceLocation(file_path=file_path, line_start=line_num)
                        ],
                        reasoning_chain=[
                            f"Matched {score} evidence-related terms",
                            line.strip(),
                        ],
                        analysis_stage="evidence_claims_extraction",
                    )
                )
        return claims

    def _extract_credibility_claims(self, lines: List[str], file_path: str) -> List[EvidenceItem]:
        claims: List[EvidenceItem] = []
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            score = sum(1 for kw in self.credibility_keywords if kw in line_lower)
            if score >= 1:
                claims.append(
                    EvidenceItem(
                        claim=f"Trust/credibility language: {line.strip()}",
                        status=EvidenceStatus.UNKNOWN,
                        evidence_type=EvidenceType.EXTRACTED,
                        confidence=ConfidenceLevel.MEDIUM,
                        source_locations=[
                            SourceLocation(file_path=file_path, line_start=line_num)
                        ],
                        reasoning_chain=[
                            f"Credibility keyword hits: {score}",
                            line.strip(),
                        ],
                        analysis_stage="credibility_claims_extraction",
                    )
                )
        return claims

    def _extract_feature_claims(self, lines: List[str], file_path: str) -> List[EvidenceItem]:
        claims: List[EvidenceItem] = []
        feature_patterns = {
            "real-time": {"category": "performance", "confidence": ConfidenceLevel.MEDIUM},
            "api": {"category": "interface", "confidence": ConfidenceLevel.HIGH},
            "database": {"category": "storage", "confidence": ConfidenceLevel.HIGH},
            "monitoring": {"category": "observability", "confidence": ConfidenceLevel.MEDIUM},
            "pattern detection": {"category": "analysis", "confidence": ConfidenceLevel.HIGH},
            "corruption detection": {"category": "civic_tech", "confidence": ConfidenceLevel.HIGH},
            "investigation": {"category": "civic_tech", "confidence": ConfidenceLevel.HIGH},
        }
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            for feature, info in feature_patterns.items():
                if feature in line_lower:
                    claims.append(
                        EvidenceItem(
                            claim=f"Feature mention: {feature}",
                            status=EvidenceStatus.UNKNOWN,
                            evidence_type=EvidenceType.EXTRACTED,
                            confidence=info["confidence"],
                            source_locations=[
                                SourceLocation(file_path=file_path, line_start=line_num)
                            ],
                            reasoning_chain=[
                                f"Category: {info['category']}",
                                line.strip(),
                            ],
                            analysis_stage="feature_claims_extraction",
                        )
                    )
        return claims

    def _assess_claim_confidence(self, capability: str) -> ConfidenceLevel:
        cap = capability.lower()
        if any(k in cap for k in self.crypto_keywords):
            return ConfidenceLevel.HIGH
        if any(k in cap for k in self.evidence_keywords):
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def _extract_keyword_context(self, line: str, keyword: str) -> str:
        line_lower = line.lower()
        pos = line_lower.find(keyword)
        if pos < 0:
            return line.strip()
        start = max(0, pos - 40)
        end = min(len(line), pos + len(keyword) + 40)
        return line[start:end].strip()


def extract_enhanced_claims(repo_path: Path) -> List[EvidenceItem]:
    """Walk README and markdown docs; return enhanced claim evidence."""
    extractor = EnhancedClaimsExtractor()
    out: List[EvidenceItem] = []
    seen: set[Path] = set()

    for doc_file in sorted(repo_path.rglob("README*")):
        if doc_file.is_file() and doc_file not in seen:
            seen.add(doc_file)
            try:
                text = doc_file.read_text(encoding="utf-8")
                out.extend(extractor.extract_claims_from_text(text, str(doc_file.resolve())))
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not read %s: %s", doc_file, e)

    extra_names = ("SECURITY.md", "CONTRIBUTING.md", "ARCHITECTURE.md")
    for name in extra_names:
        for doc_file in repo_path.rglob(name):
            if doc_file.is_file() and doc_file not in seen:
                seen.add(doc_file)
                try:
                    text = doc_file.read_text(encoding="utf-8")
                    out.extend(extractor.extract_claims_from_text(text, str(doc_file.resolve())))
                except Exception as e:  # noqa: BLE001
                    logger.warning("Could not read %s: %s", doc_file, e)

    for doc_file in sorted(repo_path.rglob("*.md")):
        if doc_file.is_file() and doc_file not in seen:
            seen.add(doc_file)
            try:
                text = doc_file.read_text(encoding="utf-8")
                out.extend(extractor.extract_claims_from_text(text, str(doc_file.resolve())))
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not read %s: %s", doc_file, e)

    return out
