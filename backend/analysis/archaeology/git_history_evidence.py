"""Emit EvidenceItem rows with source_class git_history after archaeology index exists."""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from analysis.archaeology.history import git_file_history_detailed
from analysis.archaeology.resolver import normalize_repo_relative_path
from analysis.archaeology.store import list_entities_for_repo_commit
from models.evidence import (
    SOURCE_CLASS_GIT_HISTORY,
    AnalysisEvidence,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    SourceLocation,
)

logger = logging.getLogger(__name__)

_MAX_GIT_EVIDENCE_ITEMS = 120


async def emit_git_history_evidence(
    analysis: AnalysisEvidence,
    *,
    repo_path: Path,
    repo_id: str,
    commit_sha: str,
) -> int:
    """
    Append git-backed evidence for indexed entities. No synthetic history when git returns [].
    Returns number of EvidenceItem rows added.
    """
    if commit_sha in ("unknown", "", None):
        return 0
    root = repo_path.expanduser().resolve()
    if not (root / ".git").exists():
        logger.info("Skipping git history evidence: not a git checkout at %s", root)
        return 0

    entities = await list_entities_for_repo_commit(repo_id, commit_sha)
    if not entities:
        return 0

    by_file: dict[str, list] = defaultdict(list)
    for ent in entities:
        by_file[normalize_repo_relative_path(ent.file_path)].append(ent)

    added = 0
    file_cache: dict[str, list[dict]] = {}

    for rel_file, ents in by_file.items():
        if added >= _MAX_GIT_EVIDENCE_ITEMS:
            break
        if rel_file not in file_cache:
            file_cache[rel_file] = await git_file_history_detailed(root, rel_file=rel_file, max_commits=15)
        log = file_cache[rel_file]
        if not log:
            continue

        recent = log[0]
        earliest = log[-1] if len(log) > 1 and log[-1]["commit_sha"] != recent["commit_sha"] else None

        for ent in ents:
            if added >= _MAX_GIT_EVIDENCE_ITEMS:
                break
            span_note = f"lines {ent.start_line}-{ent.end_line}"
            claim_recent = (
                f"Git history: commit {recent['commit_sha'][:7]} touched {rel_file} "
                f"({ent.qualified_name}, {span_note}) — {recent['subject']!r} "
                f"(author {recent.get('author', '?')}, {recent.get('authored_at', '')})"
            )
            strength = "moderate"
            analysis.all_evidence.append(
                EvidenceItem(
                    claim=claim_recent,
                    status=EvidenceStatus.SUPPORTED,
                    evidence_type=EvidenceType.OBSERVED,
                    confidence=ConfidenceLevel.HIGH,
                    source_locations=[
                        SourceLocation(
                            file_path=rel_file,
                            line_start=ent.start_line,
                            line_end=ent.end_line,
                        )
                    ],
                    reasoning_chain=[
                        "git log -- path (file-level)",
                        f"entity_id={ent.entity_id}",
                    ],
                    analysis_stage="git_history_extraction",
                    source_class=SOURCE_CLASS_GIT_HISTORY,
                    linked_entity_ids=[ent.entity_id],
                    support_strength=strength,
                    derived_from_code=True,
                    derived_from_doc=False,
                    refinement_signal="git_observed",
                )
            )
            added += 1

            if earliest and added < _MAX_GIT_EVIDENCE_ITEMS:
                claim_old = (
                    f"Earliest commit in retrieved history for {rel_file} ({ent.qualified_name}): "
                    f"{earliest['commit_sha'][:7]} — {earliest['subject']!r} "
                    f"(author {earliest.get('author', '?')})"
                )
                analysis.all_evidence.append(
                    EvidenceItem(
                        claim=claim_old,
                        status=EvidenceStatus.SUPPORTED,
                        evidence_type=EvidenceType.OBSERVED,
                        confidence=ConfidenceLevel.MEDIUM,
                        source_locations=[
                            SourceLocation(
                                file_path=rel_file,
                                line_start=ent.start_line,
                                line_end=ent.end_line,
                            )
                        ],
                        reasoning_chain=["git log (file-level, oldest in window)", f"entity_id={ent.entity_id}"],
                        analysis_stage="git_history_extraction",
                        source_class=SOURCE_CLASS_GIT_HISTORY,
                        linked_entity_ids=[ent.entity_id],
                        support_strength="moderate",
                        derived_from_code=True,
                        derived_from_doc=False,
                        refinement_signal="git_observed",
                    )
                )
                added += 1

    logger.info("Emitted %s git_history evidence items for %s", added, repo_id)
    return added
