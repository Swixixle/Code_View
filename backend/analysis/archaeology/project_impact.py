"""Conservative blast-radius over reverse static edges."""

from __future__ import annotations

from collections import deque

from sqlalchemy import select

from database import get_session
from models.db_models import CodeEntityRecord, EntityRelationRecord


async def shallow_transitive_dependents(
    *,
    entity_id: str,
    repo_id: str,
    commit_sha: str,
    max_depth: int = 2,
) -> tuple[list[str], list[dict]]:
    """
    BFS over incoming `calls` and `imports` edges (likely affected callers/importers).
    Does not prove runtime behaviour.
    """
    frontier: deque[tuple[str, int]] = deque([(entity_id, 0)])
    seen: set[str] = set()
    order: list[str] = []

    while frontier:
        cur, depth = frontier.popleft()
        if cur in seen:
            continue
        if depth > max_depth:
            continue
        seen.add(cur)
        if cur != entity_id:
            order.append(cur)

        if depth == max_depth:
            continue

        async with get_session() as session:
            stmt = select(EntityRelationRecord).where(
                EntityRelationRecord.repo_id == repo_id,
                EntityRelationRecord.commit_sha == commit_sha,
                EntityRelationRecord.target_entity_id == cur,
                EntityRelationRecord.relation_type.in_(["calls", "imports"]),
            )
            incoming = list((await session.execute(stmt)).scalars().all())

        for rel in incoming:
            nxt = rel.source_entity_id
            if nxt not in seen:
                frontier.append((nxt, depth + 1))

    meta: list[dict] = []
    async with get_session() as session:
        for eid in order:
            row = (await session.execute(select(CodeEntityRecord).where(CodeEntityRecord.entity_id == eid))).scalar_one_or_none()
            if row:
                meta.append(
                    {
                        "entity_id": row.entity_id,
                        "qualified_name": row.qualified_name,
                        "entity_kind": row.entity_kind,
                        "file_path": row.file_path,
                        "start_line": row.start_line,
                        "end_line": row.end_line,
                    }
                )
    return order, meta
