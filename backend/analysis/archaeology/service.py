"""Orchestrate extraction + graph build + persistence."""

from __future__ import annotations

from pathlib import Path

from analysis.archaeology.extractor import extract_repository
from analysis.archaeology.graph_builder import collect_relations
from analysis.archaeology.store import persist_archaeology_full


async def ingest_repository(
    repo_path: Path,
    *,
    repo_id: str,
    commit_sha: str,
) -> dict:
    bundle = extract_repository(repo_path)
    drafts = collect_relations(repo_path, bundle.entities)

    n_ent, n_rel = await persist_archaeology_full(
        repo_id=repo_id,
        commit_sha=commit_sha,
        entities=bundle.entities,
        drafts=drafts,
    )

    return {
        "entities_extracted": n_ent,
        "relations_stored": n_rel,
        "files_scanned": bundle.files_scanned,
    }
