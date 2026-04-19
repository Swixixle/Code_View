"""End-to-end: git repo → analyze/ingest → resolve → identify/trace data → history packet → search ranking."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest


def _git_init_commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "arch@test.local"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Arch Test"],
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
def test_archaeology_flow_resolve_identify_trace_interpret_search(tmp_path: Path) -> None:
    repo = tmp_path / "mini_repo"
    repo.mkdir()
    (repo / "signing.py").write_text(
        "# Module preamble so file span exceeds function span (resolver tie-break).\n"
        "# See verify_helper for payload checks.\n"
        "\n"
        'def verify_helper(data: bytes) -> bool:\n'
        '    """Verify signed payloads."""\n'
        "    return True\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        "This project implements Ed25519 signing and verification for all helpers.\n",
        encoding="utf-8",
    )
    _git_init_commit(repo, "add verify_helper for payload signing")

    async def _run() -> None:
        from analysis.archaeology.history import entity_git_history_packet
        from analysis.archaeology.ids import stable_repo_id
        from analysis.archaeology.resolver import resolve_line_to_entity
        from analysis.archaeology.store import get_entity_by_id, list_relations_for_entity
        from analysis.evidence import AnalysisEngine
        from analysis.ingestion.pipeline import run_analysis_pipeline
        from database import init_database
        from persistence.service import persistence_service

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
        assert pr.analysis.commit_hash not in ("unknown", "")
        assert pr.persisted

        repo_id = stable_repo_id(str(repo.resolve()))
        sha = pr.analysis.commit_hash

        res = await resolve_line_to_entity(
            repo_id=repo_id,
            commit_sha=sha,
            file_path="signing.py",
            line=6,
        )
        assert res.ok and res.primary
        assert res.primary["symbol_name"] == "verify_helper"

        eid = res.primary["entity_id"]
        row = await get_entity_by_id(eid)
        assert row is not None
        assert row.qualified_name.endswith("verify_helper")

        out, inc = await list_relations_for_entity(
            eid, repo_id=repo_id, commit_sha=sha, direction="both"
        )
        assert isinstance(out, list) and isinstance(inc, list)
        assert any(r.relation_type == "contains" for r in inc) or any(
            r.relation_type == "calls" for r in out + inc
        ), "expected at least one static contains or call edge for a nested function"

        packet, precision = await entity_git_history_packet(
            repo,
            rel_file="signing.py",
            start_line=row.start_line,
            end_line=row.end_line,
            max_commits=12,
        )
        assert packet, "expected real git history"
        assert packet[0]["source_class"] == "git_history"
        assert packet[0]["derived_from_code"] is True
        assert precision in ("line", "file")

        git_items = [e for e in pr.analysis.all_evidence if e.source_class == "git_history"]
        assert git_items, "pipeline should emit git_history evidence"

        aid = pr.analysis.analysis_id
        hits = await persistence_service.search_evidence("signing", analysis_id=aid, limit=30)
        assert hits
        classes = [h["source_class"] for h in hits]
        idx_doc = next((i for i, c in enumerate(classes) if c == "documentation_claim"),999)
        idx_git = next((i for i, c in enumerate(classes) if c == "git_history"), 999)
        idx_code = next((i for i, c in enumerate(classes) if c == "code_definition"), 999)
        assert min(idx_git, idx_code) < idx_doc, "code or git should rank before README claim"

        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        interp = client.get(
            f"/api/analysis/entity/{eid}/interpret",
            params={"repo_path": str(repo.resolve())},
        )
        assert interp.status_code == 200
        body = interp.json()
        assert body["observed_evolution"], "interpret should surface real git commits"
        assert all(x.get("source_class") == "git_history" for x in body["observed_evolution"])
        assert body.get("history_precision") in ("line", "file")

        ident = client.get(f"/api/analysis/entity/{eid}/identify")
        assert ident.status_code == 200
        ij = ident.json()
        assert ij["entity_id"] == eid
        assert ij["file_path"] == "signing.py"
        assert "line_span" in ij

        tr = client.get(f"/api/analysis/entity/{eid}/trace")
        assert tr.status_code == 200
        tj = tr.json()
        assert "contains" in tj and "contained_by" in tj
        assert isinstance(tj["contains"], list) and isinstance(tj["contained_by"], list)

    asyncio.run(_run())
