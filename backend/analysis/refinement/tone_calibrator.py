"""Calibrate institutional language to evidence quality (avoid over-claiming)."""

from __future__ import annotations

from typing import Any, Dict


class ToneCalibrator:
    """Maps classification + dedup stats to conservative institutional wording."""

    def __init__(self) -> None:
        self.institutional_language = {
            "high_quality": {
                "suitability": "Suitable for structured institutional review",
                "confidence": "Evidence density supports",
                "recommendation": "Proceed to targeted verification on priority findings",
                "trust_descriptor": "Strong evidence base for",
            },
            "moderate_quality": {
                "suitability": "Suitable for collaborative or preliminary review",
                "confidence": "Moderate evidence density suggests",
                "recommendation": "Additional verification before high-stakes conclusions",
                "trust_descriptor": "Evidence supports preliminary assessment of",
            },
            "low_quality": {
                "suitability": "Requires enhancement before broad institutional use",
                "confidence": "Limited evidence density indicates",
                "recommendation": "Treat as screening signals; expand review scope",
                "trust_descriptor": "Preliminary signals suggest",
            },
        }

        self.analysis_disclaimers = {
            "heuristic_heavy": (
                "Heuristic pattern matching is used throughout. Findings are signals "
                "for review, not definitive security or correctness verdicts."
            ),
            "pattern_focused": (
                "Many items are pattern-level matches. Manual verification is "
                "recommended before security-critical or compliance decisions."
            ),
            "implementation_focused": (
                "A substantial share of items align with implementation-like signals. "
                "Technical review remains appropriate for security properties."
            ),
            "mixed_evidence": (
                "This run mixes implementation-like and pattern-level findings. "
                "Weight items using each evidence item's refinement signal and provenance."
            ),
        }

    def _implementation_share(self, classification_summary: Dict[str, Any]) -> float:
        combined = classification_summary.get("implementation_combined", {})
        if isinstance(combined, dict) and "percentage" in combined:
            return float(combined["percentage"])
        verified = classification_summary.get("verified_implementations", {}).get("percentage", 0)
        likely = classification_summary.get("likely_implementations", {}).get("percentage", 0)
        return float(verified) + float(likely)

    def calibrate_dossier_language(
        self, analysis, classification_summary: Dict[str, Any], dedup_stats: Dict[str, Any]
    ) -> Dict[str, str]:
        quality_level = self._assess_evidence_quality(classification_summary, dedup_stats)
        analysis_type = self._determine_analysis_type(classification_summary)

        lang = self.institutional_language[quality_level]
        return {
            "quality_level": quality_level,
            "analysis_type": analysis_type,
            "institutional_suitability": lang["suitability"],
            "confidence_language": lang["confidence"],
            "recommendation": lang["recommendation"],
            "trust_descriptor": lang["trust_descriptor"],
            "disclaimer": self.analysis_disclaimers[analysis_type],
            "methodology_note": self._generate_methodology_note(quality_level, analysis_type),
        }

    def _assess_evidence_quality(
        self, classification_summary: Dict[str, Any], dedup_stats: Dict[str, Any]
    ) -> str:
        if not classification_summary or classification_summary.get("error"):
            return "low_quality"

        impl_pct = self._implementation_share(classification_summary)
        uncertain_percentage = classification_summary.get("uncertain_items", {}).get("percentage", 0)
        reduction_percentage = dedup_stats.get("reduction_percentage", 0)
        original_count = dedup_stats.get("original_count", 0)

        quality_score = 0
        if impl_pct >= 40:
            quality_score += 3
        elif impl_pct >= 20:
            quality_score += 2
        elif impl_pct >= 10:
            quality_score += 1

        if uncertain_percentage <= 10:
            quality_score += 2
        elif uncertain_percentage <= 25:
            quality_score += 1

        if original_count >= 500:
            quality_score += 1

        if 20 <= reduction_percentage <= 60:
            quality_score += 1
        elif reduction_percentage > 80:
            quality_score -= 1

        if quality_score >= 5:
            return "high_quality"
        if quality_score >= 3:
            return "moderate_quality"
        return "low_quality"

    def _determine_analysis_type(self, classification_summary: Dict[str, Any]) -> str:
        if not classification_summary or classification_summary.get("error"):
            return "heuristic_heavy"

        impl_pct = self._implementation_share(classification_summary)
        pattern_percentage = classification_summary.get("detected_patterns", {}).get("percentage", 0)
        uncertain_percentage = classification_summary.get("uncertain_items", {}).get("percentage", 0)

        if impl_pct >= 50:
            return "implementation_focused"
        if pattern_percentage >= 60:
            return "pattern_focused"
        if uncertain_percentage >= 30:
            return "heuristic_heavy"
        return "mixed_evidence"

    def _generate_methodology_note(self, quality_level: str, analysis_type: str) -> str:
        base = (
            "Forensic pipeline: Python AST extraction, documentation claims, "
            "deduplication, and pattern vs implementation labeling. "
        )
        if analysis_type == "implementation_focused":
            return (
                base + "Signals skew toward implementation-like items; "
                "still validate critical trust boundaries manually."
            )
        if analysis_type == "pattern_focused":
            return (
                base + "Signals skew toward pattern detection; "
                "use counts as triage, not denominators for compliance."
            )
        if analysis_type == "heuristic_heavy":
            return base + "High residual uncertainty — prioritize manual review on material claims."
        return base + "Mixed signals — interpret each item with its source location and refinement label."

    def generate_calibrated_trust_score(
        self, original_score: int, quality_level: str, classification_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        quality_adjustments = {"high_quality": 0, "moderate_quality": -10, "low_quality": -20}
        adjusted_score = max(0, min(100, original_score + quality_adjustments[quality_level]))

        if quality_level == "high_quality":
            confidence_range = f"{adjusted_score - 5} to {adjusted_score + 5}"
            confidence_note = "Tighter confidence interval given labeling + deduplication context"
        elif quality_level == "moderate_quality":
            confidence_range = f"{adjusted_score - 10} to {adjusted_score + 10}"
            confidence_note = "Wider interval — verify representative files for major claims"
        else:
            confidence_range = f"{adjusted_score - 15} to {adjusted_score + 15}"
            confidence_note = "Wide interval — quantitative summary is indicative only"

        return {
            "score": adjusted_score,
            "original_score": original_score,
            "confidence_range": confidence_range,
            "confidence_note": confidence_note,
            "quality_level": quality_level,
        }

    def generate_institutional_assessment_language(
        self, calibrated_trust: Dict[str, Any], quality_level: str
    ) -> str:
        score = calibrated_trust["score"]

        if quality_level == "high_quality":
            if score >= 80:
                return (
                    "Suitable for adversarial institutional review when combined with "
                    "spot validation of top findings and cryptographic touchpoints."
                )
            if score >= 60:
                return (
                    "Suitable for collaborative institutional review; add verification "
                    "where claims affect external commitments."
                )
            return "Strengthen evidence where gaps remain before broad institutional reliance."

        if quality_level == "moderate_quality":
            if score >= 70:
                return (
                    "Suitable as a preliminary institutional packet — confirm material "
                    "claims before publication or enforcement-adjacent use."
                )
            if score >= 50:
                return (
                    "Useful for structured discussion; expect supplemental evidence before "
                    "final determinations."
                )
            return "Insufficient density for institutional conclusions without further analysis."

        if score >= 60:
            return (
                "Provides investigative leads; extensive verification recommended before "
                "reliance outside the technical team."
            )
        return "Limited evidence base — expand scope or deepen review before institutional use."


def calibrate_analysis_tone(analysis, classification_summary: Dict[str, Any], dedup_stats: Dict[str, Any]) -> Dict[str, Any]:
    calibrator = ToneCalibrator()
    calibrated_language = calibrator.calibrate_dossier_language(
        analysis, classification_summary, dedup_stats
    )
    original_trust_score = getattr(analysis, "trust_score", 75)
    calibrated_trust = calibrator.generate_calibrated_trust_score(
        original_trust_score,
        calibrated_language["quality_level"],
        classification_summary,
    )
    institutional_assessment = calibrator.generate_institutional_assessment_language(
        calibrated_trust,
        calibrated_language["quality_level"],
    )

    return {
        "calibrated_language": calibrated_language,
        "calibrated_trust_score": calibrated_trust,
        "institutional_assessment": institutional_assessment,
        "quality_summary": {
            "evidence_quality": calibrated_language["quality_level"],
            "analysis_type": calibrated_language["analysis_type"],
            "confidence_level": calibrated_trust["confidence_note"],
        },
    }
