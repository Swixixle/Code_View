"""Human-facing review priorities and executive-style summaries."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

from models.evidence import EvidenceItem

logger = logging.getLogger(__name__)


class HumanReviewGenerator:
    """Surfaces top items for manual adjudication."""

    def __init__(self) -> None:
        self.crypto_keywords = [
            "ed25519",
            "sha256",
            "blake2",
            "signature",
            "signing",
            "verify",
            "verification",
            "hash",
            "digest",
            "cryptographic",
            "receipt",
            "proof",
            "attestation",
        ]
        self.implementation_keywords = [
            "function",
            "class",
            "method",
            "import",
            "return",
            "def ",
            "async def",
        ]

    def generate_executive_summary(
        self,
        analysis,
        classification_summary: Dict[str, Any],
        calibrated_tone: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "confidence_assessment": self._generate_confidence_assessment(
                classification_summary, calibrated_tone
            ),
            "top_findings": {
                "verified_implementations": self._get_top_implementations(analysis.all_evidence),
                "cryptographic_infrastructure": self._get_top_crypto_findings(analysis.all_evidence),
                "potential_contradictions": self._get_top_contradictions(analysis.contradictions),
                "requires_manual_review": self._get_uncertain_areas(analysis.all_evidence),
            },
            "review_priorities": self._generate_review_priorities(
                analysis.all_evidence, analysis.contradictions
            ),
            "quality_indicators": self._generate_quality_indicators(analysis, classification_summary),
            "next_steps": self._generate_next_steps(calibrated_tone),
        }

    def _get_top_implementations(self, evidence_items: List[EvidenceItem]) -> List[Dict[str, Any]]:
        implementations = [
            item
            for item in evidence_items
            if item.refinement_signal in ("verified_implementation", "likely_implementation")
            or (
                getattr(item.confidence, "value", item.confidence) == "high"
                and any(k in item.claim.lower() for k in self.implementation_keywords)
            )
        ]
        implementations.sort(
            key=lambda x: (
                self._get_confidence_score(x.confidence),
                len(x.claim),
                self._count_implementation_signals(x.claim),
            ),
            reverse=True,
        )
        return [
            {
                "claim": self._clean_claim(x.claim),
                "confidence": x.confidence.value if hasattr(x.confidence, "value") else x.confidence,
                "refinement_signal": x.refinement_signal,
                "source": self._format_source_location(x.source_locations),
                "review_note": "Validate symbol and call sites against security assumptions",
            }
            for x in implementations[:10]
        ]

    def _get_top_crypto_findings(self, evidence_items: List[EvidenceItem]) -> List[Dict[str, Any]]:
        crypto_items = [
            item
            for item in evidence_items
            if any(k in item.claim.lower() for k in self.crypto_keywords)
            and getattr(item.confidence, "value", item.confidence) in ("high", "medium")
        ]
        crypto_groups: dict[str, list[EvidenceItem]] = defaultdict(list)
        for item in crypto_items:
            crypto_groups[self._identify_crypto_type(item.claim)].append(item)

        top_crypto: List[EvidenceItem] = []
        for _ctype, items in crypto_groups.items():
            items.sort(
                key=lambda x: (self._get_confidence_score(x.confidence), len(x.claim)),
                reverse=True,
            )
            top_crypto.extend(items[:2])

        top_crypto.sort(key=lambda x: self._get_confidence_score(x.confidence), reverse=True)
        return [
            {
                "claim": self._clean_claim(c.claim),
                "crypto_type": self._identify_crypto_type(c.claim),
                "confidence": c.confidence.value if hasattr(c.confidence, "value") else c.confidence,
                "source": self._format_source_location(c.source_locations),
                "refinement_signal": c.refinement_signal,
            }
            for c in top_crypto[:10]
        ]

    def _get_top_contradictions(self, contradictions) -> List[Dict[str, Any]]:
        if not contradictions:
            return []
        severity_order = {"high": 3, "medium": 2, "low": 1}

        def ckey(c):
            return (
                severity_order.get(getattr(c, "severity", "low").lower(), 0),
                len(getattr(c, "description", "") or ""),
            )

        sorted_c = sorted(contradictions, key=ckey, reverse=True)
        return [
            {
                "title": getattr(c, "title", "Contradiction"),
                "description": getattr(c, "description", "")[:400],
                "severity": getattr(c, "severity", "medium"),
                "review_note": "Reconcile documentation or implementation against claim",
            }
            for c in sorted_c[:10]
        ]

    def _get_uncertain_areas(self, evidence_items: List[EvidenceItem]) -> List[Dict[str, Any]]:
        uncertain_items = [
            item
            for item in evidence_items
            if item.refinement_signal in ("uncertain", "detected_pattern", None)
            or getattr(item.confidence, "value", item.confidence) == "low"
        ]
        groups: dict[str, list[EvidenceItem]] = defaultdict(list)
        for item in uncertain_items:
            fp = item.source_locations[0].file_path if item.source_locations else "unknown"
            groups[fp].append(item)

        areas = []
        for file_path, items in groups.items():
            if len(items) < 2:
                continue
            areas.append(
                {
                    "area": file_path.split("/")[-1] if "/" in file_path else file_path,
                    "uncertain_items_count": len(items),
                    "sample_claims": [self._clean_claim(i.claim) for i in items[:3]],
                    "review_priority": "high" if len(items) >= 5 else "medium",
                }
            )
        areas.sort(key=lambda x: x["uncertain_items_count"], reverse=True)
        return areas[:5]

    def _generate_confidence_assessment(
        self, classification_summary: Dict[str, Any], calibrated_tone: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not classification_summary or classification_summary.get("error"):
            return {
                "overall_confidence": "low",
                "primary_concern": "Insufficient classification context",
                "recommendation": "Manual review required for material claims",
            }

        impl = classification_summary.get("implementation_combined", {}).get("percentage")
        if impl is None:
            v = classification_summary.get("verified_implementations", {}).get("percentage", 0)
            l = classification_summary.get("likely_implementations", {}).get("percentage", 0)
            impl = v + l

        uncertain_pct = classification_summary.get("uncertain_items", {}).get("percentage", 0)

        if impl >= 40 and uncertain_pct <= 20:
            return {
                "overall_confidence": "high",
                "primary_concern": "Implementation-like share is healthy — verify trust boundaries",
                "recommendation": "Prioritize crypto and contradiction items next",
            }
        if impl >= 20 and uncertain_pct <= 40:
            return {
                "overall_confidence": "medium",
                "primary_concern": "Mixed implementation vs pattern signals",
                "recommendation": "Review by refinement_signal and source file",
            }
        return {
            "overall_confidence": "low",
            "primary_concern": "High pattern-to-implementation ratio or uncertainty",
            "recommendation": "Broaden manual verification before external reliance",
        }

    def _generate_review_priorities(self, all_evidence, contradictions) -> List[Dict[str, str]]:
        priorities: List[Dict[str, str]] = []
        if contradictions:
            priorities.append(
                {
                    "priority": "1",
                    "area": "Documentation vs implementation",
                    "action": f"Review {len(contradictions)} contradiction records for material claims",
                    "impact": "Credibility of public-facing assertions",
                }
            )
        cryptoish = [e for e in all_evidence if e.refinement_signal != "detected_pattern" and any(
            k in e.claim.lower() for k in ["sign", "verify", "hash", "crypto", "key"]
        )]
        if cryptoish:
            priorities.append(
                {
                    "priority": "2",
                    "area": "Cryptographic touchpoints",
                    "action": "Validate signing, verification, and key-handling paths",
                    "impact": "Trust and integrity boundaries",
                }
            )
        uncertain = [e for e in all_evidence if e.refinement_signal == "uncertain"]
        if len(uncertain) >= 5:
            priorities.append(
                {
                    "priority": "3",
                    "area": "Ambiguous items",
                    "action": f"Sample or triage {min(len(uncertain), 50)} uncertain items",
                    "impact": "Reduces false confidence in headline counts",
                }
            )
        return priorities

    def _generate_quality_indicators(
        self, analysis, classification_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        total_evidence = len(analysis.all_evidence)
        files = len(
            {e.source_locations[0].file_path for e in analysis.all_evidence if e.source_locations}
        )
        return {
            "evidence_density": f"{total_evidence} items across {files} files",
            "implementation_like_share": (
                f"{classification_summary.get('implementation_combined', {}).get('percentage', 0):.0f}%"
                if classification_summary
                else "n/a"
            ),
            "pipeline_stages": len(getattr(analysis, "stages_completed", []) or []),
        }

    def _generate_next_steps(self, calibrated_tone: Dict[str, Any]) -> List[str]:
        q = calibrated_tone.get("quality_summary", {}).get("evidence_quality", "low_quality")
        if q == "high_quality":
            return [
                "Spot-check top implementation and crypto items in primary modules.",
                "Close contradiction loop where documentation implies guarantees.",
            ]
        if q == "moderate_quality":
            return [
                "Expand manual review on uncertain files; re-run after fixes.",
                "Prefer verified/likely signals when citing numbers externally.",
            ]
        return [
            "Treat headline counts as directional; avoid single-number narratives.",
            "Deepen review on security-relevant modules before institutional use.",
        ]

    def _clean_claim(self, claim: str) -> str:
        prefixes = [
            "Evidence-first language (heuristic): ",
            "Cryptographic/security documentation: ",
            "Trust/credibility language: ",
            "Implementation detail: ",
        ]
        cleaned = claim
        for p in prefixes:
            if cleaned.startswith(p):
                cleaned = cleaned[len(p) :].strip()
        if len(cleaned) > 180:
            return cleaned[:177] + "..."
        return cleaned

    def _format_source_location(self, locations) -> str:
        if not locations:
            return "unknown"
        loc = locations[0]
        name = loc.file_path.split("/")[-1] if "/" in loc.file_path else loc.file_path
        return f"{name}:{loc.line_start}"

    def _get_confidence_score(self, confidence) -> int:
        vals = {"high": 3, "medium": 2, "low": 1}
        if hasattr(confidence, "value"):
            return vals.get(confidence.value, 1)
        return vals.get(confidence, 1)

    def _identify_crypto_type(self, claim: str) -> str:
        cl = claim.lower()
        if "ed25519" in cl or "signature" in cl or "sign" in cl:
            return "digital_signatures"
        if "sha256" in cl or "hash" in cl or "digest" in cl:
            return "hashing"
        if "verify" in cl or "verification" in cl:
            return "verification"
        return "general_crypto"

    def _count_implementation_signals(self, claim: str) -> int:
        return sum(1 for k in self.implementation_keywords if k in claim.lower())


def generate_human_review_layer(
    analysis, classification_summary: Dict[str, Any], calibrated_tone: Dict[str, Any]
) -> Dict[str, Any]:
    gen = HumanReviewGenerator()
    return gen.generate_executive_summary(analysis, classification_summary, calibrated_tone)
