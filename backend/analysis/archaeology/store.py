"""Persist entities and relations (async SQLAlchemy)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select

from analysis.archaeology.extractor import ExtractedEntity
from analysis.archaeology.graph_builder import RelationDraft
from analysis.archaeology.ids import make_entity_id, make_relation_id
from database import get_session
from models.db_models import CodeEntityRecord, EntityRelationRecord


async def persist_archaeology_full(
    *,
    repo_id: str,
    commit_sha: str,
    entities: list[ExtractedEntity],
    drafts: list[RelationDraft],
) -> tuple[int, int]:
    """Clear snapshot, insert entities and relation drafts in one transaction."""
    await clear_archaeology_snapshot(repo_id, commit_sha)

    now = datetime.now(timezone.utc)
    qual_to_id: dict[str, str] = {}
    for ex in entities:
        qual_to_id[ex.qualified_name] = make_entity_id(
            repo_id, commit_sha, ex.qualified_name, ex.file_path, ex.start_line
        )

    resolved_rels = relations_from_drafts(drafts, qual_to_id)

    ent_rows: list[CodeEntityRecord] = []
    for ex in entities:
        eid = qual_to_id[ex.qualified_name]
        pid: str | None = None
        if ex.parent_qualified_name and ex.parent_qualified_name in qual_to_id:
            cand = qual_to_id[ex.parent_qualified_name]
            pid = None if cand == eid else cand

        ent_rows.append(
            CodeEntityRecord(
                entity_id=eid,
                repo_id=repo_id,
                commit_sha=commit_sha,
                language="python",
                entity_kind=ex.entity_kind,
                symbol_name=ex.symbol_name,
                qualified_name=ex.qualified_name,
                file_path=ex.file_path,
                start_line=ex.start_line,
                end_line=ex.end_line,
                parent_entity_id=pid,
                content_hash=ex.content_hash,
                signature_hash=ex.signature_hash,
                structural_hash=ex.structural_hash,
                created_at_analysis=now,
                last_seen_commit=commit_sha,
                analysis_confidence="high",
                raw_content=ex.raw_content[:100_000] if ex.raw_content else None,
                normalized_content=(ex.normalized_content[:100_000] if ex.normalized_content else None),
                docstring=ex.docstring[:50_000] if ex.docstring else None,
            )
        )

    rel_rows: list[EntityRelationRecord] = []
    for src_id, tgt_id, rtype, conf, ev in resolved_rels:
        rel_rows.append(
            EntityRelationRecord(
                relation_id=make_relation_id(repo_id, commit_sha, src_id, tgt_id, rtype),
                repo_id=repo_id,
                commit_sha=commit_sha,
                source_entity_id=src_id,
                target_entity_id=tgt_id,
                relation_type=rtype,
                confidence=conf,
                evidence_json=ev,
                discovered_at_commit=commit_sha,
                created_at_analysis=now,
            )
        )

    async with get_session() as session:
        session.add_all(ent_rows)
        session.add_all(rel_rows)
        await session.commit()

    return len(ent_rows), len(rel_rows)


async def clear_archaeology_snapshot(repo_id: str, commit_sha: str) -> None:
    async with get_session() as session:
        await session.execute(
            delete(EntityRelationRecord).where(
                EntityRelationRecord.repo_id == repo_id,
                EntityRelationRecord.commit_sha == commit_sha,
            )
        )
        await session.execute(
            delete(CodeEntityRecord).where(
                CodeEntityRecord.repo_id == repo_id,
                CodeEntityRecord.commit_sha == commit_sha,
            )
        )
        await session.commit()


def relations_from_drafts(
    drafts: list[RelationDraft],
    qual_to_id: dict[str, str],
) -> list[tuple[str, str, str, str, dict]]:
    out: list[tuple[str, str, str, str, dict]] = []
    for d in drafts:
        sid = qual_to_id.get(d.source_qual)
        tid = qual_to_id.get(d.target_qual or "")
        if not sid or not tid:
            continue
        out.append((sid, tid, d.relation_type, d.confidence, d.evidence))
    return out


async def get_entity_by_id(entity_id: str) -> CodeEntityRecord | None:
    async with get_session() as session:
        r = await session.execute(select(CodeEntityRecord).where(CodeEntityRecord.entity_id == entity_id))
        return r.scalar_one_or_none()


async def list_child_entities(parent_entity_id: str) -> list[CodeEntityRecord]:
    async with get_session() as session:
        r = await session.execute(
            select(CodeEntityRecord).where(CodeEntityRecord.parent_entity_id == parent_entity_id)
        )
        return list(r.scalars().all())


async def list_entities_for_repo_commit(repo_id: str, commit_sha: str) -> list[CodeEntityRecord]:
    async with get_session() as session:
        r = await session.execute(
            select(CodeEntityRecord).where(
                CodeEntityRecord.repo_id == repo_id,
                CodeEntityRecord.commit_sha == commit_sha,
            )
        )
        return list(r.scalars().all())


async def list_relations_for_entity(
    entity_id: str,
    *,
    repo_id: str,
    commit_sha: str,
    direction: str = "both",
) -> tuple[list[EntityRelationRecord], list[EntityRelationRecord]]:
    """Returns (outgoing, incoming) or filtered by direction."""
    async with get_session() as session:
        out: list[EntityRelationRecord] = []
        inc: list[EntityRelationRecord] = []
        if direction in ("out", "both"):
            ro = await session.execute(
                select(EntityRelationRecord).where(
                    EntityRelationRecord.repo_id == repo_id,
                    EntityRelationRecord.commit_sha == commit_sha,
                    EntityRelationRecord.source_entity_id == entity_id,
                )
            )
            out = list(ro.scalars().all())
        if direction in ("in", "both"):
            ri = await session.execute(
                select(EntityRelationRecord).where(
                    EntityRelationRecord.repo_id == repo_id,
                    EntityRelationRecord.commit_sha == commit_sha,
                    EntityRelationRecord.target_entity_id == entity_id,
                )
            )
            inc = list(ri.scalars().all())
        return out, inc
