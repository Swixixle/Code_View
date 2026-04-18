"""Focused tests for archaeology extraction, hashing, resolution, and API smoke."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text(
        '"""module doc"""\n\n'
        "def outer():\n"
        "    def inner():\n"
        "        pass\n"
        "    return inner\n"
        "\n"
        "class C:\n"
        "    def meth(self):\n"
        "        pass\n",
        encoding="utf-8",
    )
    return tmp_path


def test_hashes_stable() -> None:
    from analysis.archaeology.hashes import content_hash_from_source, sha256_hex

    a = content_hash_from_source("x = 1\n")
    b = content_hash_from_source("x =   1")
    assert a == b
    assert len(sha256_hex("test")) == 64


def test_extract_sample_tree(sample_repo: Path) -> None:
    from analysis.archaeology.extractor import extract_from_file

    ents = extract_from_file(sample_repo, sample_repo / "pkg" / "mod.py")
    kinds = {e.entity_kind for e in ents}
    assert "module" in kinds
    assert "function" in kinds
    assert "class" in kinds
    assert "method" in kinds


@pytest.mark.asyncio
async def test_resolve_innermost(sample_repo: Path) -> None:
    from database import init_database
    from analysis.archaeology.ids import make_entity_id, stable_repo_id
    from analysis.archaeology.resolver import resolve_line_to_entity
    from analysis.archaeology.store import persist_archaeology_full
    from analysis.archaeology.extractor import extract_from_file
    from analysis.archaeology.graph_builder import collect_relations

    await init_database()
    repo_id = stable_repo_id(str(sample_repo.resolve()))
    commit = "c" * 40
    ents = extract_from_file(sample_repo, sample_repo / "pkg" / "mod.py")
    drafts = collect_relations(sample_repo, ents)
    await persist_archaeology_full(repo_id=repo_id, commit_sha=commit, entities=ents, drafts=drafts)

    # Line inside inner()
    res = await resolve_line_to_entity(
        repo_id=repo_id,
        commit_sha=commit,
        file_path="pkg/mod.py",
        line=4,
    )
    assert res.ok and res.primary
    assert res.primary["entity_kind"] == "function"
    assert res.primary["symbol_name"] == "inner"

    eid = make_entity_id(repo_id, commit, res.primary["qualified_name"], res.primary["file_path"], res.primary["start_line"])
    assert eid == res.primary["entity_id"]


def test_analyze_resolve_smoke() -> None:
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
