"""Orchestrate deduplication, classification, tone calibration, and human review summary."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from analysis.refinement.evidence_deduplicator import deduplicate_analysis_evidence
from analysis.refinement.human_review_generator import generate_human_review_layer
from analysis.refinement.pattern_verification_classifier import classify_evidence_patterns
from analysis.refinement.tone_calibrator import calibrate_analysis_tone

logger = logging.getLogger(__name__)


class AnalysisRefinement:
    """Applies refinement steps and stores a compact metadata bundle on the analysis."""

    def __init__(self) -> None:
        self.refinement_stats: Dict[str, Any] = {}

    def apply_comprehensive_refinement(self, analysis) -> Dict[str, Any]:
        logger.info("Applying evidence refinement (dedupe → classify → tone → human review)")

        dedup_stats = deduplicate_analysis_evidence(analysis)
        self.refinement_stats["deduplication"] = dedup_stats

        classification_summary = classify_evidence_patterns(analysis)
        self.refinement_stats["classification"] = classification_summary

        calibrated_tone = calibrate_analysis_tone(analysis, classification_summary, dedup_stats)
        self.refinement_stats["tone_calibration"] = calibrated_tone

        human_review = generate_human_review_layer(analysis, classification_summary, calibrated_tone)
        self.refinement_stats["human_review"] = human_review

        bundle = {
            "deduplication": dedup_stats,
            "classification": classification_summary,
            "tone_calibration": calibrated_tone,
            "human_review": human_review,
            "quality_headline": self._quality_headline(
                dedup_stats, classification_summary, calibrated_tone, human_review
            ),
        }
        analysis.refinement_metadata = bundle
        return bundle

    def _quality_headline(
        self, dedup: dict, classification: dict, tone: dict, human_review: dict
    ) -> str:
        red = dedup.get("reduction_percentage", 0)
        impl = classification.get("implementation_combined", {}).get("percentage") if classification else None
        if impl is None:
            impl = 0.0
        qual = tone.get("quality_summary", {}).get("evidence_quality", "unknown")
        conf = human_review.get("confidence_assessment", {}).get("overall_confidence", "unknown")
        return (
            f"Dedup ~{red:.0f}% reduction; ~{impl:.0f}% implementation-like signals; "
            f"quality={qual}; review_confidence={conf}"
        )


def apply_analysis_refinement(analysis) -> Dict[str, Any]:
    """Entry point used by `AnalysisEngine` after raw evidence collection."""
    ref = AnalysisRefinement()
    return ref.apply_comprehensive_refinement(analysis)
