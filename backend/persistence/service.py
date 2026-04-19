"""Async persistence for `AnalysisEvidence`."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from database import get_session
from models.db_models import (
    AnalysisRecord,
    ClaimRecord,
    CodeEntityRecord,
    ContradictionRecord,
    EvidenceRecord,
    EntityRelationRecord,
    MechanismRecord,
    RepositoryMonitorRecord,
)
from analysis.integrity_signals import infer_integrity_fields
from models.evidence import AnalysisEvidence, provenance_label_for_source_class, source_class_rank
from models.orm_converters import orm_to_pydantic, pydantic_to_orm

logger = logging.getLogger(__name__)


def _synthetic_claim_for_relation(rel: EntityRelationRecord, src_qn: str, tgt_qn: str) -> str:
    if rel.relation_type == "calls":
        return f"Static analysis resolved call edge: {src_qn} -> {tgt_qn}"
    if rel.relation_type == "imports":
        return f"Static analysis resolved import edge: {src_qn} imports {tgt_qn}"
    if rel.relation_type == "contains":
        return f"Static analysis containment edge: {src_qn} contains {tgt_qn}"
    return f"Static relation {rel.relation_type}: {src_qn} -> {tgt_qn}"


def _synthetic_code_definition_dict(ent: CodeEntityRecord) -> dict:
    claim = f"Indexed {ent.entity_kind} definition: {ent.qualified_name}"
    d: dict = {
        "id": f"_synthetic_code_definition:{ent.entity_id}",
        "claim": claim,
        "claim_full_length": len(claim),
        "status": "supported",
        "confidence": "high",
        "evidence_type": "observed",
        "analysis_stage": "archaeology_entity_view",
        "source_class": "code_definition",
        "provenance_label": provenance_label_for_source_class("code_definition"),
        "source_locations": [
            {
                "file_path": ent.file_path,
                "line_start": ent.start_line,
                "line_end": ent.end_line,
            }
        ],
        "linked_entity_ids": [ent.entity_id],
        "linked_relation_ids": [],
        "refinement_signal": "indexed_entity_anchor",
        "boundary_note": "Synthesized from code_entities row for entity-scoped evidence view.",
        "derived_from_doc": False,
        "derived_from_code": True,
        "support_strength": "strong",
        "synthetic": True,
    }
    d.update(infer_integrity_fields(claim))
    return d


def _local_repo_root_for_analysis(repository_url: str) -> Path | None:
    """Return a git checkout path if analysis was run against a local disk repo."""
    raw = (repository_url or "").strip()
    if not raw:
        return None
    if raw.startswith("file://"):
        from urllib.parse import unquote, urlparse

        parsed = urlparse(raw)
        path = unquote(parsed.path or "")
        if parsed.netloc and len(path) > 2 and path[0] == "/" and path[2] == ":":
            path = path.lstrip("/")
        root = Path(path)
    else:
        if raw.startswith("http://") or raw.startswith("https://"):
            return None
        root = Path(raw)
    try:
        root = root.expanduser().resolve()
    except OSError:
        return None
    if root.is_dir() and (root / ".git").exists():
        return root
    return None


def _synthetic_git_history_dicts(
    ent: CodeEntityRecord, packet: list[dict], precision: str
) -> list[dict]:
    """One compact evidence row per packet commit, mirroring Interpret / git_history_extraction."""
    out: list[dict] = []
    for i, row in enumerate(packet):
        sha_full = (row.get("commit_sha") or "").strip()
        sha_short = sha_full[:7] if len(sha_full) >= 7 else sha_full or f"idx{i}"
        subj = row.get("subject", "")
        author = row.get("author", "?")
        authored = row.get("authored_at", "")
        src = row.get("source", "git")
        claim = (
            f"Git history ({precision}-level via {src}): {sha_short} — {subj!r} "
            f"(author {author}, {authored}); span {ent.qualified_name} "
            f"lines {ent.start_line}-{ent.end_line}"
        )
        eid = ent.entity_id
        hid = f"_synthetic_git_history:{eid}:{sha_full or i}:{i}"
        row_d: dict = {
            "id": hid,
            "claim": claim[:500] + ("…" if len(claim) > 500 else ""),
            "claim_full_length": len(claim),
            "status": "supported",
            "confidence": "high",
            "evidence_type": "observed",
            "analysis_stage": "entity_git_history_synthetic",
            "source_class": "git_history",
            "provenance_label": provenance_label_for_source_class("git_history"),
            "source_locations": [
                {
                    "file_path": ent.file_path,
                    "line_start": ent.start_line,
                    "line_end": ent.end_line,
                }
            ],
            "linked_entity_ids": [eid],
            "linked_relation_ids": [],
            "refinement_signal": "git_observed",
            "boundary_note": (
                "Synthesized from entity_git_history_packet for entity-scoped evidence; "
                "same commits as Interpret when the checkout path matches analysis."
            ),
            "derived_from_doc": False,
            "derived_from_code": True,
            "support_strength": "moderate",
            "synthetic": True,
            "history_precision": precision,
        }
        row_d.update(infer_integrity_fields(claim))
        out.append(row_d)
    return out


def _synthetic_code_relation_dict(
    rel: EntityRelationRecord, src: CodeEntityRecord, tgt: CodeEntityRecord
) -> dict:
    claim = _synthetic_claim_for_relation(rel, src.qualified_name, tgt.qualified_name)
    strength = "strong" if rel.confidence == "high" else "moderate"
    d: dict = {
        "id": f"_synthetic_code_relation:{rel.relation_id}",
        "claim": claim,
        "claim_full_length": len(claim),
        "status": "supported",
        "confidence": "high" if strength == "strong" else "medium",
        "evidence_type": "observed",
        "analysis_stage": "relation_graph_evidence_synthetic",
        "source_class": "code_relation",
        "provenance_label": provenance_label_for_source_class("code_relation"),
        "source_locations": [
            {
                "file_path": src.file_path,
                "line_start": src.start_line,
                "line_end": src.end_line,
            }
        ],
        "linked_entity_ids": [rel.source_entity_id, rel.target_entity_id],
        "linked_relation_ids": [rel.relation_id],
        "refinement_signal": "static_relation_edge",
        "boundary_note": "Synthesized from persisted entity_relations; complements capped relation evidence rows.",
        "derived_from_doc": False,
        "derived_from_code": True,
        "support_strength": strength,
        "synthetic": True,
    }
    d.update(infer_integrity_fields(claim))
    return d


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

    async def get_analysis_repo_identity(self, analysis_id: str) -> Optional[tuple[str, str]]:
        """Return (repository_url, commit_hash) for archaeology scoping, or None if missing."""
        try:
            async with get_session() as session:
                stmt = select(AnalysisRecord.repository_url, AnalysisRecord.commit_hash).where(
                    AnalysisRecord.id == analysis_id
                )
                row = (await session.execute(stmt)).one_or_none()
                if row is None:
                    return None
                return str(row[0]), str(row[1])
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to read analysis scope %s: %s", analysis_id, e)
            return None

    async def get_evidence_item(self, evidence_id: str) -> Optional[dict]:
        try:
            async with get_session() as session:
                stmt = select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
                result = await session.execute(stmt)
                er = result.scalar_one_or_none()
                if not er:
                    return None
                claim_full = er.claim or ""
                d = {
                    "id": er.id,
                    "analysis_id": er.analysis_id,
                    "claim": claim_full,
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
                d.update(infer_integrity_fields(claim_full))
                return d
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
                    claim_full = r.claim or ""
                    d = {
                        "id": r.id,
                        "analysis_id": r.analysis_id,
                        "claim": claim_full,
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
                    d.update(infer_integrity_fields(claim_full))
                    return d

                decorated = [(source_class_rank(getattr(r, "source_class", None)), -r.timestamp.timestamp(), r) for r in rows]
                decorated.sort(key=lambda t: (t[0], t[1]))
                ranked = [t[2] for t in decorated]
                return [row_to_dict(r) for r in ranked[:limit]]
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to search evidence: %s", e)
            return []

    async def get_evidence_for_entity(
        self, analysis_id: str, entity_id: str, *, limit: int = 120
    ) -> list[dict]:
        """Persisted evidence linked to entity, plus synthetic code/git anchors when gaps exist."""
        try:
            from analysis.archaeology.store import get_entity_by_id, list_relations_for_entity

            ent = await get_entity_by_id(entity_id)
            if not ent:
                return []

            out, inc = await list_relations_for_entity(
                entity_id,
                repo_id=ent.repo_id,
                commit_sha=ent.commit_sha,
                direction="both",
            )
            rel_by_id: dict[str, EntityRelationRecord] = {}
            for rel in out + inc:
                rel_by_id[rel.relation_id] = rel
            all_rels = list(rel_by_id.values())
            rel_ids_touching = set(rel_by_id.keys())

            async with get_session() as session:
                stmt = select(EvidenceRecord).where(EvidenceRecord.analysis_id == analysis_id)
                rows = list((await session.execute(stmt)).scalars().all())

            matched: list[EvidenceRecord] = []
            seen: set[str] = set()
            for r in rows:
                lids = list(getattr(r, "linked_entity_ids", None) or [])
                rids = list(getattr(r, "linked_relation_ids", None) or [])
                hit = entity_id in lids or (
                    bool(rel_ids_touching) and bool(set(rids) & rel_ids_touching)
                )
                if hit and r.id not in seen:
                    seen.add(r.id)
                    matched.append(r)

            def row_to_dict(r: EvidenceRecord) -> dict:
                sc = getattr(r, "source_class", None) or "keyword_heuristic"
                claim = r.claim or ""
                d = {
                    "id": r.id,
                    "claim": claim[:500] + ("…" if len(claim) > 500 else ""),
                    "claim_full_length": len(claim),
                    "status": r.status,
                    "confidence": r.confidence,
                    "evidence_type": r.evidence_type,
                    "analysis_stage": r.analysis_stage,
                    "source_class": sc,
                    "provenance_label": provenance_label_for_source_class(sc),
                    "source_locations": r.source_locations or [],
                    "linked_entity_ids": (getattr(r, "linked_entity_ids", None) or [])[:30],
                    "linked_relation_ids": (getattr(r, "linked_relation_ids", None) or [])[:30],
                    "refinement_signal": getattr(r, "refinement_signal", None),
                    "boundary_note": (r.boundary_note or "")[:400],
                    "derived_from_doc": bool(getattr(r, "derived_from_doc", False)),
                    "derived_from_code": bool(getattr(r, "derived_from_code", False)),
                    "support_strength": getattr(r, "support_strength", None) or "weak",
                    "synthetic": False,
                }
                d.update(infer_integrity_fields(claim))
                return d

            persisted_rel_cov: set[str] = set()
            for r in matched:
                for rid in getattr(r, "linked_relation_ids", None) or []:
                    persisted_rel_cov.add(rid)

            has_persisted_code_def = any(
                getattr(r, "source_class", None) == "code_definition"
                and entity_id in (getattr(r, "linked_entity_ids", None) or [])
                for r in matched
            )

            need_ids: set[str] = {entity_id}
            for rel in all_rels:
                if rel.relation_id not in persisted_rel_cov:
                    need_ids.add(rel.source_entity_id)
                    need_ids.add(rel.target_entity_id)

            ent_cache: dict[str, CodeEntityRecord | None] = {}
            for eid in need_ids:
                ent_cache[eid] = await get_entity_by_id(eid)

            synthetics: list[dict] = []

            if ent.entity_kind in ("function", "method", "class", "route") and not has_persisted_code_def:
                synthetics.append(_synthetic_code_definition_dict(ent))

            for rel in all_rels:
                if rel.relation_id in persisted_rel_cov:
                    continue
                if rel.relation_type not in ("calls", "imports", "contains"):
                    continue
                if rel.relation_type in ("calls", "imports") and rel.confidence not in (
                    "high",
                    "medium",
                ):
                    continue
                src = ent_cache.get(rel.source_entity_id)
                tgt = ent_cache.get(rel.target_entity_id)
                if not src or not tgt:
                    continue
                synthetics.append(_synthetic_code_relation_dict(rel, src, tgt))

            has_git_history_row = any(
                getattr(r, "source_class", None) == "git_history" for r in matched
            )
            if not has_git_history_row:
                scope = await self.get_analysis_repo_identity(analysis_id)
                if scope:
                    repo_url, _a_commit = scope
                    root = _local_repo_root_for_analysis(repo_url)
                    if root is not None:
                        from analysis.archaeology.history import entity_git_history_packet
                        from analysis.archaeology.resolver import normalize_repo_relative_path

                        rel_norm = normalize_repo_relative_path(ent.file_path)
                        try:
                            packet, prec = await entity_git_history_packet(
                                root,
                                rel_file=rel_norm,
                                start_line=ent.start_line,
                                end_line=ent.end_line,
                                max_commits=12,
                            )
                        except Exception as git_exc:  # noqa: BLE001
                            logger.debug("entity_git_history_packet skipped: %s", git_exc)
                            packet, prec = [], "none"
                        if packet:
                            synthetics.extend(_synthetic_git_history_dicts(ent, packet, prec))

            combined = [row_to_dict(r) for r in matched] + synthetics
            combined.sort(key=lambda d: (source_class_rank(d.get("source_class")), d.get("id", "")))
            return combined[:limit]
        except Exception as e:  # noqa: BLE001
            logger.error("get_evidence_for_entity failed: %s", e)
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
