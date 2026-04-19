"""Classify evidence as implementation-like vs pattern / heuristic signals."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from models.evidence import EvidenceItem

logger = logging.getLogger(__name__)


class PatternVerificationClassifier:
    """Labels items with refinement_signal without replacing EvidenceType enums."""

    def __init__(self) -> None:
        self.classification_stats: dict[str, int] = {
            "total_classified": 0,
            "verified_implementations": 0,
            "likely_implementations": 0,
            "detected_patterns": 0,
            "uncertain_classifications": 0,
        }

        self.implementation_indicators = {
            "function_definitions": ["def ", "function ", "class ", "async def"],
            "imports": ["import ", "from "],
            "method_calls": [".sign(", ".verify(", ".hash(", ".digest("],
            "crypto_libraries": ["cryptography", "ed25519", "hashlib", "secrets"],
            "return_statements": ["return ", "yield "],
        }

        self.pattern_indicators = {
            "comments": ["#", "//", '"""', "'''"],
            "variable_names": ["_sign", "_verify", "_hash", "signature", "digest"],
            "config_mentions": ["config", "setting", "option", "parameter"],
        }

    def classify_evidence(self, evidence_items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Attach `refinement_signal` and optional boundary note context."""
        classified: List[EvidenceItem] = []

        for item in evidence_items:
            # Documentation is never upgraded to verified_implementation by keyword scoring.
            if getattr(item, "source_class", None) == "documentation_claim":
                if item.refinement_signal not in ("doc_entity_linked",):
                    item.refinement_signal = item.refinement_signal or "doc_only_claim"
                classified.append(item)
                continue

            if getattr(item, "source_class", None) == "git_history":
                classified.append(item)
                continue

            if getattr(item, "source_class", None) == "code_relation":
                classified.append(item)
                continue

            info = self._classify_single_item(item)
            signal = info["signal"]
            item.refinement_signal = signal

            note_extra = info["reasoning"]
            if item.boundary_note:
                item.boundary_note = f"{item.boundary_note} | Signal: {note_extra}"
            else:
                item.boundary_note = f"Signal: {note_extra}"

            classified.append(item)

            if signal == "verified_implementation":
                self.classification_stats["verified_implementations"] += 1
            elif signal == "likely_implementation":
                self.classification_stats["likely_implementations"] += 1
            elif signal == "detected_pattern":
                self.classification_stats["detected_patterns"] += 1
            else:
                self.classification_stats["uncertain_classifications"] += 1

        self.classification_stats["total_classified"] = len(classified)
        return classified

    def _classify_single_item(self, item: EvidenceItem) -> Dict[str, str]:
        claim = item.claim.lower()
        source_info = self._get_source_context(item)

        implementation_score = self._calculate_implementation_score(claim, source_info)
        pattern_score = self._calculate_pattern_score(claim, source_info)

        if implementation_score >= 3:
            return {
                "signal": "verified_implementation",
                "reasoning": f"implementation_score={implementation_score} (structure/calls/libraries)",
            }
        if implementation_score >= 1 and pattern_score < 2:
            return {
                "signal": "likely_implementation",
                "reasoning": f"implementation_score={implementation_score}, pattern_score={pattern_score}",
            }
        if pattern_score >= 2:
            return {
                "signal": "detected_pattern",
                "reasoning": f"pattern_score={pattern_score} (doc/comment/naming/context)",
            }
        return {
            "signal": "uncertain",
            "reasoning": f"ambiguous (impl={implementation_score}, pattern={pattern_score})",
        }

    def _calculate_implementation_score(self, claim: str, source_info: dict) -> int:
        score = 0

        for indicator in self.implementation_indicators["function_definitions"]:
            if indicator in claim:
                score += 3
                break

        for indicator in self.implementation_indicators["imports"]:
            if indicator in claim:
                score += 2
                break

        for indicator in self.implementation_indicators["method_calls"]:
            if indicator in claim:
                score += 3
                break

        for indicator in self.implementation_indicators["crypto_libraries"]:
            if indicator in claim:
                score += 2

        for indicator in self.implementation_indicators["return_statements"]:
            if indicator in claim:
                score += 1

        if source_info["is_python_file"]:
            score += 1
        if source_info["is_implementation_file"]:
            score += 1

        return score

    def _calculate_pattern_score(self, claim: str, source_info: dict) -> int:
        score = 0

        if source_info["is_documentation"]:
            score += 2

        for indicator in self.pattern_indicators["comments"]:
            if indicator in claim:
                score += 1
                break

        variable_count = sum(
            1 for indicator in self.pattern_indicators["variable_names"] if indicator in claim
        )
        if variable_count >= 2:
            score += 2
        elif variable_count == 1:
            score += 1

        for indicator in self.pattern_indicators["config_mentions"]:
            if indicator in claim:
                score += 1

        if len(claim) < 30:
            score += 1

        return score

    def _get_source_context(self, item: EvidenceItem) -> dict:
        context = {
            "is_python_file": False,
            "is_documentation": False,
            "is_implementation_file": False,
            "file_path": "",
        }

        if not item.source_locations:
            return context

        file_path = item.source_locations[0].file_path.lower()
        context["file_path"] = file_path
        context["is_python_file"] = file_path.endswith(".py")

        doc_indicators = [".md", "readme", "contributing", "docs/", "documentation"]
        context["is_documentation"] = any(indicator in file_path for indicator in doc_indicators)

        impl_indicators = ["/src/", "/lib/", "/analysis/", "/api/", "/models/", "/services/"]
        context["is_implementation_file"] = any(
            indicator in file_path for indicator in impl_indicators
        )

        return context

    def generate_classification_summary(self) -> Dict[str, Any]:
        """Summary compatible with tone calibration (verified + likely → implementation share)."""
        total = self.classification_stats["total_classified"]
        if total == 0:
            return {"error": "No items classified"}

        verified_impl = self.classification_stats["verified_implementations"]
        likely_impl = self.classification_stats["likely_implementations"]
        pattern_ct = self.classification_stats["detected_patterns"]
        uncertain_ct = self.classification_stats["uncertain_classifications"]

        implementation_total = verified_impl + likely_impl

        return {
            "total_items": total,
            "verified_implementations": {
                "count": verified_impl,
                "percentage": (verified_impl / total) * 100,
            },
            "likely_implementations": {
                "count": likely_impl,
                "percentage": (likely_impl / total) * 100,
            },
            "implementation_combined": {
                "count": implementation_total,
                "percentage": (implementation_total / total) * 100,
            },
            "detected_patterns": {
                "count": pattern_ct,
                "percentage": (pattern_ct / total) * 100,
            },
            "uncertain_items": {
                "count": uncertain_ct,
                "percentage": (uncertain_ct / total) * 100,
            },
            "quality_assessment": self._assess_classification_quality(
                implementation_total, pattern_ct, uncertain_ct, total
            ),
        }

    def _assess_classification_quality(
        self, implementation_total: int, pattern_ct: int, uncertain_ct: int, total: int
    ) -> str:
        verified_ratio = implementation_total / total if total else 0
        uncertain_ratio = uncertain_ct / total if total else 0
        pattern_ratio = pattern_ct / total if total else 0

        if verified_ratio >= 0.4:
            return "High implementation density — stronger adjudication base"
        if verified_ratio >= 0.2:
            return "Moderate implementation density — mixed evidence base"
        if uncertain_ratio >= 0.3:
            return "High uncertainty — prioritize manual review"
        if pattern_ratio >= 0.5:
            return "Pattern-heavy — treat counts as screening signals, not ground truth"
        return "Mixed signals — review by refinement_signal"


def classify_evidence_patterns(analysis) -> dict:
    """Run classification on `analysis.all_evidence`."""
    classifier = PatternVerificationClassifier()
    analysis.all_evidence = classifier.classify_evidence(analysis.all_evidence)
    summary = classifier.generate_classification_summary()
    logger.info(
        "Pattern/verification classification: %s implementation-class, %s pattern",
        summary.get("implementation_combined", {}).get("count", 0),
        summary.get("detected_patterns", {}).get("count", 0),
    )
    return summary
