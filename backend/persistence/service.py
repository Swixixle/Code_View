"""Async persistence for `AnalysisEvidence`."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from database import get_session
from models.db_models import (
    AnalysisRecord,
    ClaimRecord,
    ContradictionRecord,
    EvidenceRecord,
    MechanismRecord,
    RepositoryMonitorRecord,
)
from models.evidence import AnalysisEvidence, provenance_label_for_source_class, source_class_rank
from models.orm_converters import orm_to_pydantic, pydantic_to_orm

logger = logging.getLogger(__name__)


class EvidencePersistenceService:
    async def store_analysis(self, analysis_evidence: AnalysisEvidence) -> bool:
        try:
            async with get_session() as session:
                await session.execute(
                    delete(AnalysisRecord).where(AnalysisRecord.id == analysis_evidence.analysis_id)
                )
                pydantic_to_orm(analysis_evidence, session)
                await session.commit()
                logger.info(
                    "Stored analysis %s (%s evidence items)",
                    analysis_evidence.analysis_id,
                    len(analysis_evidence.all_evidence),
                )
                return True
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to store analysis %s: %s", analysis_evidence.analysis_id, e)
            return False

    async def get_analysis(self, analysis_id: str) -> Optional[AnalysisEvidence]:
        try:
            async with get_session() as session:
                stmt = (
                    select(AnalysisRecord)
                    .options(
                        selectinload(AnalysisRecord.evidence_items),
                        selectinload(AnalysisRecord.claims),
                        selectinload(AnalysisRecord.contradictions),
                        selectinload(AnalysisRecord.mechanisms),
                    )
                    .where(AnalysisRecord.id == analysis_id)
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if not row:
                    return None
                return orm_to_pydantic(row)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to retrieve analysis %s: %s", analysis_id, e)
            return None

    async def get_evidence_item(self, evidence_id: str) -> Optional[dict]:
        try:
            async with get_session() as session:
                stmt = select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
                result = await session.execute(stmt)
                er = result.scalar_one_or_none()
                if not er:
                    return None
                return {
                    "id": er.id,
                    "analysis_id": er.analysis_id,
                    "claim": er.claim,
                    "status": er.status,
                    "evidence_type": er.evidence_type,
                    "confidence": er.confidence,
                    "source_locations": er.source_locations,
                    "extracted_symbols": er.extracted_symbols,
                    "reasoning_chain": er.reasoning_chain,
                    "counterevidence": er.counterevidence,
                    "analysis_stage": er.analysis_stage,
                    "boundary_note": er.boundary_note,
                    "timestamp": er.timestamp.isoformat(),
                    "last_verified": er.last_verified.isoformat(),
                    "source_class": getattr(er, "source_class", None) or "keyword_heuristic",
                    "linked_entity_ids": getattr(er, "linked_entity_ids", None) or [],
                    "linked_relation_ids": getattr(er, "linked_relation_ids", None) or [],
                    "support_strength": getattr(er, "support_strength", None) or "weak",
                    "derived_from_doc": bool(getattr(er, "derived_from_doc", False)),
                    "derived_from_code": bool(getattr(er, "derived_from_code", False)),
                    "provenance_label": provenance_label_for_source_class(
                        getattr(er, "source_class", None) or "keyword_heuristic"
                    ),
                    "refinement_signal": getattr(er, "refinement_signal", None),
                }
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to retrieve evidence %s: %s", evidence_id, e)
            return None

    async def list_analyses(
        self, repository_url: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        try:
            async with get_session() as session:
                stmt = select(AnalysisRecord).order_by(AnalysisRecord.analysis_started.desc())
                if repository_url:
                    stmt = stmt.where(AnalysisRecord.repository_url == repository_url)
                stmt = stmt.limit(limit)
                result = await session.execute(stmt)
                records = result.scalars().all()

                analyses: list[dict] = []
                for record in records:
                    aid = record.id
                    ec = await session.scalar(
                        select(func.count())
                        .select_from(EvidenceRecord)
                        .where(EvidenceRecord.analysis_id == aid)
                    )
                    cc = await session.scalar(
                        select(func.count())
                        .select_from(ClaimRecord)
                        .where(ClaimRecord.analysis_id == aid)
                    )
                    xc = await session.scalar(
                        select(func.count())
                        .select_from(ContradictionRecord)
                        .where(ContradictionRecord.analysis_id == aid)
                    )
                    analyses.append(
                        {
                            "analysis_id": record.id,
                            "repository_url": record.repository_url,
                            "commit_hash": record.commit_hash,
                            "branch": record.branch,
                            "analysis_started": record.analysis_started.isoformat(),
                            "analysis_completed": record.analysis_completed.isoformat()
                            if record.analysis_completed
                            else None,
                            "analysis_duration": record.analysis_duration,
                            "coverage_percentage": record.coverage_percentage,
                            "stages_completed": record.stages_completed,
                            "stages_failed": record.stages_failed,
                            "evidence_count": ec or 0,
                            "claims_count": cc or 0,
                            "contradictions_count": xc or 0,
                        }
                    )
                return analyses
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to list analyses: %s", e)
            return []

    async def search_evidence(
        self, query: str, analysis_id: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        try:
            async with get_session() as session:
                stmt = select(EvidenceRecord).where(EvidenceRecord.claim.contains(query))
                if analysis_id:
                    stmt = stmt.where(EvidenceRecord.analysis_id == analysis_id)
                # Fetch more than limit so source-aware ranking can promote code before docs
                stmt = stmt.order_by(EvidenceRecord.timestamp.desc()).limit(max(limit * 8, 200))
                result = await session.execute(stmt)
                rows = list(result.scalars().all())

                def row_to_dict(r: EvidenceRecord) -> dict:
                    sc = getattr(r, "source_class", None) or "keyword_heuristic"
                    return {
                        "id": r.id,
                        "analysis_id": r.analysis_id,
                        "claim": r.claim,
                        "status": r.status,
                        "confidence": r.confidence,
                        "evidence_type": r.evidence_type,
                        "analysis_stage": r.analysis_stage,
                        "timestamp": r.timestamp.isoformat(),
                        "source_locations": (r.source_locations or [])[:3],
                        "source_class": sc,
                        "linked_entity_ids": (getattr(r, "linked_entity_ids", None) or [])[:20],
                        "linked_relation_ids": (getattr(r, "linked_relation_ids", None) or [])[:20],
                        "support_strength": getattr(r, "support_strength", None) or "weak",
                        "derived_from_doc": bool(getattr(r, "derived_from_doc", False)),
                        "derived_from_code": bool(getattr(r, "derived_from_code", False)),
                        "provenance_label": provenance_label_for_source_class(sc),
                    }

                decorated = [(source_class_rank(getattr(r, "source_class", None)), -r.timestamp.timestamp(), r) for r in rows]
                decorated.sort(key=lambda t: (t[0], t[1]))
                ranked = [t[2] for t in decorated]
                return [row_to_dict(r) for r in ranked[:limit]]
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to search evidence: %s", e)
            return []

    async def get_repository_monitoring(self, repository_url: str) -> Optional[dict]:
        try:
            async with get_session() as session:
                stmt = select(RepositoryMonitorRecord).where(
                    RepositoryMonitorRecord.repository_url == repository_url
                )
                result = await session.execute(stmt)
                m = result.scalar_one_or_none()
                if not m:
                    return None
                return {
                    "repository_url": m.repository_url,
                    "last_check": m.last_check.isoformat(),
                    "last_commit": m.last_commit,
                    "check_interval": m.check_interval,
                    "monitoring_enabled": m.monitoring_enabled,
                    "created_at": m.created_at.isoformat(),
                    "updated_at": m.updated_at.isoformat(),
                }
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to get repository monitoring: %s", e)
            return None

    async def set_repository_monitoring(
        self, repository_url: str, check_interval: int = 300, enabled: bool = True
    ) -> bool:
        try:
            from datetime import datetime

            async with get_session() as session:
                stmt = select(RepositoryMonitorRecord).where(
                    RepositoryMonitorRecord.repository_url == repository_url
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                now = datetime.now()
                if row:
                    row.check_interval = check_interval
                    row.monitoring_enabled = enabled
                    row.updated_at = now
                else:
                    session.add(
                        RepositoryMonitorRecord(
                            repository_url=repository_url,
                            last_check=now,
                            check_interval=check_interval,
                            monitoring_enabled=enabled,
                        )
                    )
                await session.commit()
                return True
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to set repository monitoring: %s", e)
            return False

    async def get_analysis_summary(self, analysis_id: str) -> Optional[dict]:
        try:
            async with get_session() as session:
                stmt = select(AnalysisRecord).where(AnalysisRecord.id == analysis_id)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                if not record:
                    return None

                evidence_count = await session.scalar(
                    select(func.count())
                    .select_from(EvidenceRecord)
                    .where(EvidenceRecord.analysis_id == analysis_id)
                )
                claims_count = await session.scalar(
                    select(func.count())
                    .select_from(ClaimRecord)
                    .where(ClaimRecord.analysis_id == analysis_id)
                )
                contradictions_count = await session.scalar(
                    select(func.count())
                    .select_from(ContradictionRecord)
                    .where(ContradictionRecord.analysis_id == analysis_id)
                )
                mechanisms_count = await session.scalar(
                    select(func.count())
                    .select_from(MechanismRecord)
                    .where(MechanismRecord.analysis_id == analysis_id)
                )

                return {
                    "analysis_id": record.id,
                    "repository_url": record.repository_url,
                    "commit_hash": record.commit_hash,
                    "branch": record.branch,
                    "analysis_started": record.analysis_started.isoformat(),
                    "analysis_completed": record.analysis_completed.isoformat()
                    if record.analysis_completed
                    else None,
                    "analysis_duration": record.analysis_duration,
                    "stages_completed": record.stages_completed,
                    "stages_failed": record.stages_failed,
                    "coverage_percentage": record.coverage_percentage,
                    "evidence_items": evidence_count or 0,
                    "claims_assembled": claims_count or 0,
                    "contradictions": contradictions_count or 0,
                    "mechanisms": mechanisms_count or 0,
                    "refinement": record.refinement_metadata,
                }
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to get analysis summary: %s", e)
            return None

    async def find_evidence_ids_for_relation(self, analysis_id: str, relation_id: str) -> list[str]:
        """Evidence rows that reference this relation_id in linked_relation_ids."""
        try:
            async with get_session() as session:
                stmt = select(EvidenceRecord).where(EvidenceRecord.analysis_id == analysis_id)
                rows = list((await session.execute(stmt)).scalars().all())
            out: list[str] = []
            for r in rows:
                lids = getattr(r, "linked_relation_ids", None) or []
                if relation_id in lids:
                    out.append(r.id)
            return out
        except Exception as e:  # noqa: BLE001
            logger.error("find_evidence_ids_for_relation failed: %s", e)
            return []


persistence_service = EvidencePersistenceService()
