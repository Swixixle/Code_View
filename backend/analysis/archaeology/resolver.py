"""Location -> entity resolution with explicit ambiguity handling."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from database import get_session
from models.db_models import CodeEntityRecord


def normalize_repo_relative_path(file_path: str) -> str:
    p = file_path.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


@dataclass
class ResolveResult:
    ok: bool
    primary: dict | None
    alternates: list[dict]
    uncertainty: list[str]


async def resolve_line_to_entity(
    *,
    repo_id: str,
    commit_sha: str,
    file_path: str,
    line: int,
    column: int | None = None,
) -> ResolveResult:
    """
    Smallest enclosing entity for (file_path, line).
    column is accepted for API compatibility; AST extraction does not refine past line.
    """
    _ = column
    norm = normalize_repo_relative_path(file_path)
    uncertainty: list[str] = []

    async with get_session() as session:
        stmt = select(CodeEntityRecord).where(
            CodeEntityRecord.repo_id == repo_id,
            CodeEntityRecord.commit_sha == commit_sha,
            CodeEntityRecord.file_path == norm,
            CodeEntityRecord.start_line <= line,
            CodeEntityRecord.end_line >= line,
        )
        rows = list((await session.execute(stmt)).scalars().all())

    if not rows:
        return ResolveResult(
            ok=False,
            primary=None,
            alternates=[],
            uncertainty=["archaeological_gap", f"No entity index for file `{norm}` at line {line} (run analyze first)."],
        )

    def span_width(e: CodeEntityRecord) -> int:
        return e.end_line - e.start_line

    rows.sort(key=lambda e: (span_width(e), -e.start_line))
    best = rows[0]
    same_tier = [
        e
        for e in rows
        if (e.end_line - e.start_line) == (best.end_line - best.start_line) and e.start_line == best.start_line
    ]
    if len(same_tier) > 1:
        uncertainty.append("ambiguous_symbol_resolution")

    def row_to_dict(e: CodeEntityRecord) -> dict:
        return {
            "entity_id": e.entity_id,
            "entity_kind": e.entity_kind,
            "symbol_name": e.symbol_name,
            "qualified_name": e.qualified_name,
            "file_path": e.file_path,
            "start_line": e.start_line,
            "end_line": e.end_line,
            "confidence": "medium" if "ambiguous_symbol_resolution" in uncertainty else "high",
        }

    primary = row_to_dict(best)
    alts = [row_to_dict(e) for e in same_tier[1:]] if len(same_tier) > 1 else []

    parent_chain: list[dict] = []
    cur: str | None = best.parent_entity_id
    async with get_session() as session:
        for _ in range(64):
            if not cur:
                break
            stmt = select(CodeEntityRecord).where(CodeEntityRecord.entity_id == cur)
            prow = (await session.execute(stmt)).scalar_one_or_none()
            if not prow:
                uncertainty.append("archaeological_gap")
                break
            parent_chain.append(
                {
                    "entity_id": prow.entity_id,
                    "qualified_name": prow.qualified_name,
                    "entity_kind": prow.entity_kind,
                    "file_path": prow.file_path,
                    "start_line": prow.start_line,
                    "end_line": prow.end_line,
                }
            )
            cur = prow.parent_entity_id

    primary["parent_chain"] = parent_chain
    return ResolveResult(ok=True, primary=primary, alternates=alts, uncertainty=uncertainty)


async def resolve_entity_id_exists(entity_id: str) -> CodeEntityRecord | None:
    async with get_session() as session:
        stmt = select(CodeEntityRecord).where(CodeEntityRecord.entity_id == entity_id)
        return (await session.execute(stmt)).scalar_one_or_none()
