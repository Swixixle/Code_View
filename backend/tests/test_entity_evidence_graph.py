"""Entity-scoped evidence merges persisted rows with graph-synthetic code items."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest


def _git_commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True)


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not installed",
)
def test_entity_evidence_lists_code_before_documentation(tmp_path: Path) -> None:
    """Small repo: callee + caller + README; evidence for callee ranks code before docs."""
    repo = tmp_path / "mini"
    repo.mkdir()
    (repo / "app.py").write_text(
        'def callee():\n'
        '    """crypto helper for payloads"""\n'
        "    return 42\n"
        "\n"
        "def caller():\n"
        "    return callee()\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        "This project implements callee-based signing for all bundles.\n",
        encoding="utf-8",
    )
    _git_commit(repo, "init")

    async def _run() -> None:
        from analysis.evidence import AnalysisEngine
        from analysis.ingestion.pipeline import run_analysis_pipeline
        from database import init_database
        from fastapi.testclient import TestClient
        from main import app

        await init_database()
        engine = AnalysisEngine()
        pr = await run_analysis_pipeline(
            engine=engine,
            repo_path=repo,
            source_for_identity=str(repo.resolve()),
            persist=True,
            monitoring=False,
            monitoring_label=str(repo.resolve()),
            run_archaeology=True,
        )
        assert pr.persisted
        aid = pr.analysis.analysis_id

        client = TestClient(app)
        es = client.get(
            "/api/analysis/entities/search",
            params={"q": "callee", "analysis_id": aid, "limit": 10},
        )
        assert es.status_code == 200
        entities = es.json().get("entities") or []
        assert entities, "expected callee entity"
        eid = entities[0]["entity_id"]

        ev = client.get(
            f"/api/analysis/entity/{eid}/evidence",
            params={"analysis_id": aid},
        )
        assert ev.status_code == 200
        items = ev.json().get("items") or []
        assert items, "expected some linked evidence"

        classes = [x.get("source_class") for x in items]
        assert "documentation_claim" in classes, "expected README-linked documentation_claim"

        idx_doc = next(i for i, c in enumerate(classes) if c == "documentation_claim")
        idx_code_def = next(
            (i for i, c in enumerate(classes) if c == "code_definition"),
            999,
        )
        idx_code_rel = next(
            (i for i, c in enumerate(classes) if c == "code_relation"),
            999,
        )
        idx_git = next(
            (i for i, c in enumerate(classes) if c == "git_history"),
            999,
        )

        assert idx_code_def < 999, "expected code_definition (persisted or synthetic anchor)"
        assert idx_code_rel < 999, "expected code_relation for caller/callee edge"
        assert min(idx_code_def, idx_code_rel, idx_git) < idx_doc, (
            "code/git evidence should rank before documentation_claim"
        )

        assert any(x.get("source_class") == "code_definition" for x in items)
        assert any(x.get("source_class") == "code_relation" for x in items)

    asyncio.run(_run())
