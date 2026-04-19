"""Emit inspectable EvidenceItem rows for persisted static graph edges (calls, imports, contains)."""

from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import select

from analysis.archaeology.store import get_entity_by_id
from database import get_session
from models.db_models import EntityRelationRecord
from models.evidence import (
    SOURCE_CLASS_CODE_RELATION,
    AnalysisEvidence,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    SourceLocation,
)

logger = logging.getLogger(__name__)

_MAX_RELATION_EVIDENCE = 250

_REL_ORDER: dict[str, int] = {"calls": 0, "imports": 1, "contains": 2}


def _support_strength(edge_conf: str) -> Literal["strong", "moderate"]:
    return "strong" if edge_conf == "high" else "moderate"


def _should_emit(rel: EntityRelationRecord) -> bool:
    if rel.relation_type == "contains":
        return True
    if rel.relation_type in ("calls", "imports"):
        return rel.confidence in ("high", "medium")
    return False


def _claim_for(rel: EntityRelationRecord, src_qn: str, tgt_qn: str) -> str:
    if rel.relation_type == "calls":
        return f"Static analysis resolved call edge: {src_qn} -> {tgt_qn}"
    if rel.relation_type == "imports":
        return f"Static analysis resolved import edge: {src_qn} imports {tgt_qn}"
    if rel.relation_type == "contains":
        return f"Static analysis containment edge: {src_qn} contains {tgt_qn}"
    return f"Static relation {rel.relation_type}: {src_qn} -> {tgt_qn}"


async def emit_relation_evidence(
    analysis: AnalysisEvidence,
    *,
    repo_id: str,
    commit_sha: str,
) -> int:
    """Append code_relation evidence items; returns count added."""
    if commit_sha in ("unknown", "", None):
        return 0

    async with get_session() as session:
        stmt = select(EntityRelationRecord).where(
            EntityRelationRecord.repo_id == repo_id,
            EntityRelationRecord.commit_sha == commit_sha,
            EntityRelationRecord.relation_type.in_(("calls", "imports", "contains")),
        )
        rows = list((await session.execute(stmt)).scalars().all())

    rows.sort(key=lambda r: (_REL_ORDER.get(r.relation_type, 9), r.relation_id))
    added = 0

    for rel in rows:
        if added >= _MAX_RELATION_EVIDENCE:
            break
        if not _should_emit(rel):
            continue
        src = await get_entity_by_id(rel.source_entity_id)
        tgt = await get_entity_by_id(rel.target_entity_id)
        if not src or not tgt:
            continue

        claim = _claim_for(rel, src.qualified_name, tgt.qualified_name)
        strength = _support_strength(rel.confidence)
        loc = SourceLocation(
            file_path=src.file_path,
            line_start=src.start_line,
            line_end=src.end_line,
        )

        analysis.all_evidence.append(
            EvidenceItem(
                claim=claim,
                status=EvidenceStatus.SUPPORTED,
                evidence_type=EvidenceType.OBSERVED,
                confidence=ConfidenceLevel.HIGH if strength == "strong" else ConfidenceLevel.MEDIUM,
                source_locations=[loc],
                reasoning_chain=[
                    f"relation_id={rel.relation_id}",
                    f"relation_type={rel.relation_type}",
                    f"edge_confidence={rel.confidence}",
                ],
                analysis_stage="relation_graph_evidence",
                source_class=SOURCE_CLASS_CODE_RELATION,
                linked_entity_ids=[rel.source_entity_id, rel.target_entity_id],
                linked_relation_ids=[rel.relation_id],
                support_strength=strength,
                derived_from_code=True,
                derived_from_doc=False,
                refinement_signal="static_relation_edge",
                boundary_note="Static graph only; dynamic dispatch not modeled.",
            )
        )
        added += 1

    logger.info("Emitted %s code_relation evidence items for %s", added, repo_id)
    return added
