"""Persist entities and relations (async SQLAlchemy)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select

from analysis.archaeology.extractor import ExtractedEntity
from analysis.archaeology.graph_builder import RelationDraft
from analysis.archaeology.ids import make_entity_id, make_relation_id
from database import get_session
from models.db_models import CodeEntityRecord, EntityRelationRecord


def _like_pattern_contains(raw: str) -> tuple[str, str]:
    """Build a case-insensitive LIKE pattern and escape char for SQLite/SQLAlchemy."""
    esc = "\\"
    escaped = (
        raw.replace(esc, esc + esc)
        .replace("%", esc + "%")
        .replace("_", esc + "_")
    )
    return f"%{escaped.lower()}%", esc


def _entity_loc_key(ex: ExtractedEntity) -> tuple[str, str, int]:
    return (ex.qualified_name, ex.file_path, ex.start_line)


def _resolve_parent_entity_id(
    ex: ExtractedEntity,
    *,
    loc_to_id: dict[tuple[str, str, int], str],
    by_qual: dict[str, list[tuple[str, str, int]]],
) -> str | None:
    pq = ex.parent_qualified_name
    if not pq:
        return None
    my = _entity_loc_key(ex)
    my_id = loc_to_id[my]
    plocs = by_qual.get(pq, [])
    if not plocs:
        return None
    uniq_locs = sorted(set(plocs))
    if len(uniq_locs) == 1:
        cand = loc_to_id[uniq_locs[0]]
        return None if cand == my_id else cand
    same_file = [lk for lk in uniq_locs if lk[1] == ex.file_path]
    pool = same_file or uniq_locs
    inner_line = my[2]
    enclosing = [lk for lk in pool if lk[2] < inner_line]
    if enclosing:
        best_loc = max(enclosing, key=lambda lk: lk[2])
        cand = loc_to_id[best_loc]
        return None if cand == my_id else cand
    cand = loc_to_id[sorted(pool)[0]]
    return None if cand == my_id else cand


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
    loc_to_id: dict[tuple[str, str, int], str] = {
        _entity_loc_key(ex): make_entity_id(
            repo_id, commit_sha, ex.qualified_name, ex.file_path, ex.start_line
        )
        for ex in entities
    }
    by_qual: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for ex in entities:
        by_qual[ex.qualified_name].append(_entity_loc_key(ex))

    qual_to_id: dict[str, str] = {}
    for q, locs in by_qual.items():
        qual_to_id[q] = loc_to_id[sorted(set(locs))[0]]

    resolved_rels = relations_from_drafts(drafts, qual_to_id)

    ent_rows: list[CodeEntityRecord] = []
    for ex in entities:
        lk = _entity_loc_key(ex)
        eid = loc_to_id[lk]
        pid = _resolve_parent_entity_id(ex, loc_to_id=loc_to_id, by_qual=by_qual)

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


async def get_relation_by_id(relation_id: str) -> EntityRelationRecord | None:
    async with get_session() as session:
        r = await session.execute(
            select(EntityRelationRecord).where(EntityRelationRecord.relation_id == relation_id)
        )
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


def _entity_search_rank(qraw: str, row: CodeEntityRecord) -> int:
    """Lower is better: exact symbol, then qual tail, symbol substring, qual, path."""
    q = qraw.strip().lower()
    sym = (row.symbol_name or "").lower()
    qual = (row.qualified_name or "").lower()
    fp = (row.file_path or "").lower()
    trail = qual.rsplit(".", 1)[-1] if qual else ""
    if sym == q:
        return 1
    if qual == q or trail == q:
        return 2
    if q in sym:
        return 3
    if q in qual:
        return 4
    if q in fp:
        return 5
    return 6


async def search_entities(
    *,
    repo_id: str,
    commit_sha: str,
    query: str,
    entity_kind: str | None = None,
    limit: int = 50,
) -> list[CodeEntityRecord]:
    """Substring match (case-insensitive) on symbol_name, qualified_name, or file_path."""
    q = query.strip()
    if not q:
        return []
    pattern, esc = _like_pattern_contains(q)
    fetch_cap = min(max(limit * 25, limit), 800)
    async with get_session() as session:
        stmt = select(CodeEntityRecord).where(
            CodeEntityRecord.repo_id == repo_id,
            CodeEntityRecord.commit_sha == commit_sha,
            or_(
                func.lower(CodeEntityRecord.symbol_name).like(pattern, escape=esc),
                func.lower(CodeEntityRecord.qualified_name).like(pattern, escape=esc),
                func.lower(CodeEntityRecord.file_path).like(pattern, escape=esc),
            ),
        )
        if entity_kind:
            stmt = stmt.where(CodeEntityRecord.entity_kind == entity_kind)
        stmt = stmt.limit(fetch_cap)
        r = await session.execute(stmt)
        rows = list(r.scalars().all())
    rows.sort(key=lambda e: (_entity_search_rank(q, e), (e.qualified_name or "")))
    return rows[:limit]


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
