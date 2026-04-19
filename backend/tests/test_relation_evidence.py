"""Relation-backed code_relation evidence, search, trace identity, and GET /relation."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest


def _git(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "r@test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "R"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not installed",
)
def test_relation_evidence_call_import_search_trace_endpoint(tmp_path: Path) -> None:
    repo = tmp_path / "rel_ev"
    (repo / "pack").mkdir(parents=True)
    (repo / "pack" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pack" / "b.py").write_text("def helper() -> int:\n    return 1\n", encoding="utf-8")
    (repo / "pack" / "a.py").write_text(
        "from pack.b import helper\n\ndef use_helper() -> int:\n    return helper()\n",
        encoding="utf-8",
    )
    _git(repo)

    async def _run() -> None:
        from sqlalchemy import delete

        from analysis.archaeology.ids import stable_repo_id
        from analysis.archaeology.resolver import resolve_line_to_entity
        from analysis.evidence import AnalysisEngine
        from analysis.ingestion.pipeline import run_analysis_pipeline
        from database import get_session, init_database
        from fastapi.testclient import TestClient
        from main import app
        from models.db_models import CodeEntityRecord, EntityRelationRecord
        from persistence.service import persistence_service

        await init_database()
        pr = await run_analysis_pipeline(
            engine=AnalysisEngine(),
            repo_path=repo,
            source_for_identity=str(repo.resolve()),
            persist=True,
            monitoring=False,
            monitoring_label=str(repo.resolve()),
            run_archaeology=True,
        )
        rid = stable_repo_id(str(repo.resolve()))
        sha = pr.analysis.commit_hash
        aid = pr.analysis.analysis_id

        rel_ev = [e for e in pr.analysis.all_evidence if e.source_class == "code_relation"]
        assert rel_ev, "expected code_relation evidence from graph"
        call_items = [e for e in rel_ev if "call edge" in e.claim]
        imp_items = [e for e in rel_ev if "import edge" in e.claim]
        assert call_items and imp_items
        assert call_items[0].linked_relation_ids
        assert len(call_items[0].linked_entity_ids) == 2

        hits = await persistence_service.search_evidence("helper", analysis_id=aid, limit=50)
        assert any(h.get("source_class") == "code_relation" for h in hits)
        assert any(h.get("linked_relation_ids") for h in hits if h.get("source_class") == "code_relation")

        res = await resolve_line_to_entity(repo_id=rid, commit_sha=sha, file_path="pack/a.py", line=4)
        assert res.ok and res.primary
        eid = res.primary["entity_id"]

        client = TestClient(app)
        tr = client.get(f"/api/analysis/entity/{eid}/trace")
        assert tr.status_code == 200
        for edge in tr.json()["callees"]:
            assert edge.get("source_entity_id")
            assert edge.get("target_entity_id")
            assert edge.get("source_class") == "code_relation"
            assert edge.get("peer_symbol_name") == "helper"

        rel_id = tr.json()["callees"][0]["relation_id"]
        detail = client.get(f"/api/analysis/relation/{rel_id}", params={"analysis_id": aid})
        assert detail.status_code == 200
        d = detail.json()
        assert d["relation_type"] == "calls"
        assert d["source_entity"] and d["target_entity"]
        assert d["linked_evidence_ids"]

        async with get_session() as session:
            await session.execute(delete(EntityRelationRecord).where(EntityRelationRecord.repo_id == rid))
            await session.execute(delete(CodeEntityRecord).where(CodeEntityRecord.repo_id == rid))
            await session.commit()

    asyncio.run(_run())


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not installed",
)
def test_contains_relation_emits_code_relation_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "cont_ev"
    repo.mkdir()
    (repo / "m.py").write_text(
        "class Box:\n"
        "    def inner(self) -> None:\n"
        "        pass\n",
        encoding="utf-8",
    )
    _git(repo)

    async def _run() -> None:
        from analysis.evidence import AnalysisEngine
        from analysis.ingestion.pipeline import run_analysis_pipeline
        from database import init_database

        await init_database()
        pr = await run_analysis_pipeline(
            engine=AnalysisEngine(),
            repo_path=repo,
            source_for_identity=str(repo.resolve()),
            persist=False,
            monitoring=False,
            monitoring_label=str(repo.resolve()),
            run_archaeology=True,
        )
        rel_ev = [e for e in pr.analysis.all_evidence if e.source_class == "code_relation"]
        assert any("containment" in e.claim for e in rel_ev)

    asyncio.run(_run())
