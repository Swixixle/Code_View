"""Link documentation_claim items to indexed CodeEntityRecord rows (annotation only, not proof)."""

from __future__ import annotations

import re

from sqlalchemy import select

from analysis.archaeology.resolver import normalize_repo_relative_path
from database import get_session
from models.db_models import CodeEntityRecord
from models.evidence import AnalysisEvidence

_PY_PATH = re.compile(r"[`~]?\s*([\w/.-]+\.py)\s*[`~]?", re.IGNORECASE)
_SKIP = frozenset(
    "the and for are but not you all can had her was one our out day get has him his how man "
    "new now see two way who boy did its let put say she too use any may per via org api sql "
    "web log doc code use".split()
)


def _paths_from_claim(claim: str) -> list[str]:
    return list(dict.fromkeys(m.group(1).replace("\\", "/") for m in _PY_PATH.finditer(claim)))


def _symbol_tokens(claim: str) -> set[str]:
    raw = re.findall(r"\b[a-z_][a-z0-9_]{2,}\b", claim.lower())
    return {t for t in raw if t not in _SKIP and len(t) > 2}


async def apply_doc_claim_entity_links(
    analysis: AnalysisEvidence,
    *,
    repo_id: str,
    commit_sha: str,
) -> int:
    """Mutate matching evidence items in place. Returns count of items linked."""
    if not commit_sha or commit_sha == "unknown":
        return 0

    linked = 0
    async with get_session() as session:
        for item in analysis.all_evidence:
            if getattr(item, "source_class", None) != "documentation_claim":
                continue
            if item.linked_entity_ids:
                continue

            paths: list[str] = []
            for loc in item.source_locations or []:
                fp = getattr(loc, "file_path", "") or ""
                if fp.lower().endswith(".md"):
                    paths.extend(_paths_from_claim(item.claim))
            paths.extend(_paths_from_claim(item.claim))
            paths = [normalize_repo_relative_path(p) for p in dict.fromkeys(paths) if p]

            symbols = _symbol_tokens(item.claim)

            stmt = select(CodeEntityRecord).where(
                CodeEntityRecord.repo_id == repo_id,
                CodeEntityRecord.commit_sha == commit_sha,
            )
            if paths:
                stmt = stmt.where(CodeEntityRecord.file_path.in_(paths))
            result = await session.execute(stmt.limit(400))
            rows = list(result.scalars().all())

            if symbols and rows:
                sym_low = {s.lower() for s in symbols}
                rows = [
                    r
                    for r in rows
                    if r.symbol_name.lower() in sym_low
                    or any(s in r.qualified_name.lower() for s in sym_low)
                ]

            if not rows and symbols and not paths:
                stmt2 = select(CodeEntityRecord).where(
                    CodeEntityRecord.repo_id == repo_id,
                    CodeEntityRecord.commit_sha == commit_sha,
                )
                cand = list((await session.execute(stmt2.limit(600))).scalars().all())
                sym_low = {s.lower() for s in symbols}
                rows = [
                    r
                    for r in cand
                    if r.symbol_name.lower() in sym_low
                    or any(s in r.qualified_name.lower() for s in sym_low)
                ][:30]

            ids: list[str] = []
            seen: set[str] = set()
            for r in rows:
                if r.entity_id not in seen:
                    seen.add(r.entity_id)
                    ids.append(r.entity_id)

            if ids:
                item.linked_entity_ids = ids[:25]
                item.support_strength = "moderate"
                item.refinement_signal = "doc_entity_linked"
                extra = "doc_entity_linked: path/symbol match to indexed entities (does not verify behavior)."
                item.boundary_note = f"{item.boundary_note} | {extra}" if item.boundary_note else extra
                linked += 1

    return linked
