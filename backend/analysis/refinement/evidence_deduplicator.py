"""Remove duplicate evidence items to provide defensible counts."""

from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from typing import List

from models.evidence import EvidenceItem

logger = logging.getLogger(__name__)


class EvidenceDeduplicator:
    """Deduplicates evidence items using multiple strategies."""

    def __init__(self) -> None:
        self.dedup_stats: dict = {
            "original_count": 0,
            "deduplicated_count": 0,
            "exact_duplicates_removed": 0,
            "semantic_duplicates_removed": 0,
            "location_consolidations": 0,
            "pattern_repetitions_removed": 0,
        }

    def deduplicate_evidence(self, evidence_items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Main deduplication pipeline."""
        self.dedup_stats["original_count"] = len(evidence_items)

        if not evidence_items:
            return evidence_items

        deduplicated = self._remove_exact_duplicates(evidence_items)
        deduplicated = self._consolidate_location_variants(deduplicated)
        deduplicated = self._remove_semantic_duplicates(deduplicated)
        before_pattern = len(deduplicated)
        deduplicated = self._remove_pattern_repetitions(deduplicated)
        self.dedup_stats["pattern_repetitions_removed"] = before_pattern - len(deduplicated)

        self.dedup_stats["deduplicated_count"] = len(deduplicated)
        return deduplicated

    def _remove_exact_duplicates(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Remove items with identical claims and source locations."""
        seen_hashes: set[str] = set()
        deduplicated: List[EvidenceItem] = []
        removed_count = 0

        for item in items:
            location_key = ""
            if item.source_locations:
                loc = item.source_locations[0]
                location_key = f"{loc.file_path}:{loc.line_start}"

            item_hash = hashlib.md5(
                f"{item.claim.strip()}{location_key}".encode(),
                usedforsecurity=False,
            ).hexdigest()

            if item_hash not in seen_hashes:
                seen_hashes.add(item_hash)
                deduplicated.append(item)
            else:
                removed_count += 1

        self.dedup_stats["exact_duplicates_removed"] = removed_count
        return deduplicated

    def _consolidate_location_variants(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Consolidate same claims appearing at multiple locations."""
        claim_groups: dict[str, list[EvidenceItem]] = defaultdict(list)

        for item in items:
            normalized_claim = self._normalize_claim_text(item.claim)
            claim_groups[normalized_claim].append(item)

        consolidated: List[EvidenceItem] = []
        consolidation_count = 0

        for _normalized_claim, group in claim_groups.items():
            if len(group) == 1:
                consolidated.append(group[0])
                continue

            primary_item = self._select_primary_evidence(group)
            all_locations: List = []
            for item in group:
                all_locations.extend(item.source_locations)
            unique_locations = self._deduplicate_locations(all_locations)
            primary_item.source_locations = unique_locations[:5]
            consolidated.append(primary_item)
            consolidation_count += len(group) - 1

        self.dedup_stats["location_consolidations"] = consolidation_count
        return consolidated

    def _remove_semantic_duplicates(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Remove items with very similar semantic meaning."""
        to_remove: set[int] = set()

        for i, item1 in enumerate(items):
            if i in to_remove:
                continue

            for j, item2 in enumerate(items[i + 1 :], i + 1):
                if j in to_remove:
                    continue

                if self._are_semantically_similar(item1.claim, item2.claim):
                    if self._get_confidence_value(item1.confidence) >= self._get_confidence_value(
                        item2.confidence
                    ):
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
                        break

        self.dedup_stats["semantic_duplicates_removed"] = len(to_remove)
        return [item for idx, item in enumerate(items) if idx not in to_remove]

    def _remove_pattern_repetitions(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Reduce repetitive pattern matches that inflate crypto-related counts."""
        pattern_indicators = [
            "signing",
            "verification",
            "cryptographic",
            "hash",
            "digest",
            "signature",
            "verify",
            "sign",
            "crypto",
            "ed25519",
            "sha256",
        ]

        file_pattern_groups: dict[str, dict[str, list[EvidenceItem]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for item in items:
            if not item.source_locations:
                continue
            file_path = item.source_locations[0].file_path
            pattern_type = None
            claim_l = item.claim.lower()
            for pattern in pattern_indicators:
                if pattern.lower() in claim_l:
                    pattern_type = pattern
                    break
            if pattern_type:
                file_pattern_groups[file_path][pattern_type].append(item)

        filtered: List[EvidenceItem] = []

        for item in items:
            if not item.source_locations:
                filtered.append(item)
                continue

            file_path = item.source_locations[0].file_path
            claim_l = item.claim.lower()
            pattern_type = None
            for pattern in pattern_indicators:
                if pattern.lower() in claim_l:
                    pattern_type = pattern
                    break

            if pattern_type and len(file_pattern_groups[file_path][pattern_type]) > 3:
                group = file_pattern_groups[file_path][pattern_type]
                best_item = max(
                    group,
                    key=lambda x: (
                        self._get_confidence_value(x.confidence),
                        len(x.claim),
                        -group.index(x),
                    ),
                )
                if item is best_item:
                    filtered.append(item)
            else:
                filtered.append(item)

        return filtered

    def _normalize_claim_text(self, claim: str) -> str:
        """Normalize claim text for comparison."""
        prefixes_to_remove = [
            "Evidence-first language (heuristic): ",
            "Cryptographic/security documentation: ",
            "Trust/credibility language: ",
            "Implementation detail: ",
            "Pattern detected: ",
        ]

        normalized = claim.strip()
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :].strip()

        return " ".join(normalized.split())

    def _select_primary_evidence(self, group: List[EvidenceItem]) -> EvidenceItem:
        """Select the best representative from a group of similar evidence."""
        stage_priority = {
            "python_parsing": 3,
            "evidence_claims_extraction": 2,
            "cryptographic_claims_extraction": 2,
            "credibility_claims_extraction": 1,
            "enhanced_python_parsing": 3,
            "cryptographic_analysis": 3,
        }

        return max(
            group,
            key=lambda item: (
                self._get_confidence_value(item.confidence),
                len(item.claim),
                stage_priority.get(item.analysis_stage, 0),
            ),
        )

    def _deduplicate_locations(self, locations: list) -> list:
        seen: set[tuple[str, int]] = set()
        unique: list = []
        for loc in locations:
            key = (loc.file_path, loc.line_start)
            if key not in seen:
                seen.add(key)
                unique.append(loc)
        return unique

    def _are_semantically_similar(self, claim1: str, claim2: str) -> bool:
        norm1 = self._normalize_claim_text(claim1).lower()
        norm2 = self._normalize_claim_text(claim2).lower()

        if len(norm1) < 20 or len(norm2) < 20:
            return False

        if norm1 in norm2 or norm2 in norm1:
            return True

        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if not words1 or not words2:
            return False

        overlap = len(words1.intersection(words2))
        min_length = min(len(words1), len(words2))
        return overlap / min_length > 0.8

    def _get_confidence_value(self, confidence) -> int:
        confidence_values = {"high": 3, "medium": 2, "low": 1}
        if hasattr(confidence, "value"):
            return confidence_values.get(confidence.value, 1)
        return confidence_values.get(confidence, 1)

    def get_deduplication_report(self) -> dict:
        """Return deduplication statistics."""
        original = self.dedup_stats["original_count"]
        reduction_percentage = 0.0
        if original > 0:
            reduction_percentage = (
                (original - self.dedup_stats["deduplicated_count"]) / original
            ) * 100

        return {
            **self.dedup_stats,
            "reduction_percentage": reduction_percentage,
            "quality_improvement": "Removed duplicate patterns and consolidated location variants",
        }


def deduplicate_analysis_evidence(analysis) -> dict:
    """Deduplicate `analysis.all_evidence` only (claims assembled later)."""
    deduplicator = EvidenceDeduplicator()
    original = len(analysis.all_evidence)
    analysis.all_evidence = deduplicator.deduplicate_evidence(analysis.all_evidence)
    report = deduplicator.get_deduplication_report()
    logger.info(
        "Evidence deduplication: %s -> %s (%.0f%% reduction)",
        original,
        report["deduplicated_count"],
        report["reduction_percentage"],
    )
    return report
