"""Entity-level imports, same-module calls, trace buckets, and static-analysis honesty."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "g@test.local"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(["git", "config", "user.name", "G"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not installed",
)
def test_import_relation_pack_b_to_a(tmp_path: Path) -> None:
    repo = tmp_path / "imp_repo"
    (repo / "pack").mkdir(parents=True)
    (repo / "pack" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pack" / "b.py").write_text(
        "def helper() -> int:\n    return 42\n",
        encoding="utf-8",
    )
    (repo / "pack" / "a.py").write_text(
        "from pack.b import helper\n\n"
        "def use_helper() -> int:\n"
        "    return helper()\n",
        encoding="utf-8",
    )
    _git_init(repo)

    async def _run() -> None:
        from sqlalchemy import delete, select

        from analysis.archaeology.ids import stable_repo_id
        from analysis.archaeology.resolver import resolve_line_to_entity
        from analysis.archaeology.store import EntityRelationRecord, list_relations_for_entity
        from analysis.evidence import AnalysisEngine
        from analysis.ingestion.pipeline import run_analysis_pipeline
        from database import get_session, init_database

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
        assert sha != "unknown"

        async with get_session() as session:
            rels = list(
                (await session.execute(select(EntityRelationRecord).where(EntityRelationRecord.repo_id == rid)))
                .scalars()
                .all()
            )
        imports = [r for r in rels if r.relation_type == "imports"]
        assert imports, "expected at least one imports relation"
        assert any(r.confidence in ("high", "medium", "low") for r in imports)
        pack_edges = [r for r in imports if r.target_entity_id]
        assert pack_edges

        res = await resolve_line_to_entity(
            repo_id=rid, commit_sha=sha, file_path="pack/a.py", line=4
        )
        assert res.ok and res.primary
        eid = res.primary["entity_id"]
        out, inc = await list_relations_for_entity(eid, repo_id=rid, commit_sha=sha, direction="both")
        assert any(r.relation_type == "calls" for r in out)

        async with get_session() as session:
            await session.execute(
                delete(EntityRelationRecord).where(EntityRelationRecord.repo_id == rid)
            )
            from models.db_models import CodeEntityRecord

            await session.execute(delete(CodeEntityRecord).where(CodeEntityRecord.repo_id == rid))
            await session.commit()

    asyncio.run(_run())


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not installed",
)
def test_trace_surfaces_calls_and_imports_with_peer_meta(tmp_path: Path) -> None:
    repo = tmp_path / "trace_repo"
    repo.mkdir()
    (repo / "mod.py").write_text(
        "def helper() -> int:\n    return 1\n\n"
        "def outer() -> int:\n"
        "    return helper()\n",
        encoding="utf-8",
    )
    _git_init(repo)

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

        res = await resolve_line_to_entity(repo_id=rid, commit_sha=sha, file_path="mod.py", line=5)
        assert res.ok and res.primary
        outer_id = res.primary["entity_id"]

        client = TestClient(app)
        tr = client.get(f"/api/analysis/entity/{outer_id}/trace")
        assert tr.status_code == 200
        body = tr.json()
        callees = body["callees"]
        assert callees, "outer -> helper call expected"
        assert any(c.get("peer_symbol_name") == "helper" for c in callees)
        assert all("confidence" in c for c in callees)

        async with get_session() as session:
            await session.execute(delete(EntityRelationRecord).where(EntityRelationRecord.repo_id == rid))
            await session.execute(delete(CodeEntityRecord).where(CodeEntityRecord.repo_id == rid))
            await session.commit()

    asyncio.run(_run())


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not installed",
)
def test_dynamic_getattr_no_high_confidence_call_edge(tmp_path: Path) -> None:
    repo = tmp_path / "dyn_repo"
    repo.mkdir()
    (repo / "dyn.py").write_text(
        "import operator\n\n"
        "def outer(x: int) -> int:\n"
        "    fn = getattr(operator, 'add')\n"
        "    return fn(x, 1)\n",
        encoding="utf-8",
    )
    _git_init(repo)

    async def _run() -> None:
        from sqlalchemy import delete, select

        from analysis.archaeology.ids import stable_repo_id
        from analysis.archaeology.resolver import resolve_line_to_entity
        from analysis.evidence import AnalysisEngine
        from analysis.ingestion.pipeline import run_analysis_pipeline
        from database import get_session, init_database
        from models.db_models import CodeEntityRecord, EntityRelationRecord

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

        calls = []
        async with get_session() as session:
            calls = list(
                (
                    await session.execute(
                        select(EntityRelationRecord).where(
                            EntityRelationRecord.repo_id == rid,
                            EntityRelationRecord.relation_type == "calls",
                        )
                    )
                )
                .scalars()
                .all()
            )

        high_to_operator_add = [
            r
            for r in calls
            if r.confidence == "high" and r.evidence_json and "add" in str(r.evidence_json)
        ]
        assert not high_to_operator_add, "should not invent high-confidence edges for dynamic getattr() calls"

        res = await resolve_line_to_entity(repo_id=rid, commit_sha=sha, file_path="dyn.py", line=5)
        if res.ok and res.primary:
            outer_id = res.primary["entity_id"]
            async with get_session() as session:
                rels = list(
                    (
                        await session.execute(
                            select(EntityRelationRecord).where(
                                EntityRelationRecord.repo_id == rid,
                                EntityRelationRecord.source_entity_id == outer_id,
                                EntityRelationRecord.relation_type == "calls",
                                EntityRelationRecord.confidence == "high",
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            assert len(rels) == 0, "outer should not have high-confidence static call to operator.add"

        async with get_session() as session:
            await session.execute(delete(EntityRelationRecord).where(EntityRelationRecord.repo_id == rid))
            await session.execute(delete(CodeEntityRecord).where(CodeEntityRecord.repo_id == rid))
            await session.commit()

    asyncio.run(_run())
