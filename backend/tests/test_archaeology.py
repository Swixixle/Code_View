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


def test_nested_functions_have_distinct_qualified_names(tmp_path: Path) -> None:
    """Regression: module-level nested defs must not share the same qualified_name."""
    m = tmp_path / "nested.py"
    m.write_text(
        "def outer_a():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner\n"
        "def outer_b():\n"
        "    def inner():\n"
        "        return 2\n"
        "    return inner\n",
        encoding="utf-8",
    )
    from analysis.archaeology.extractor import extract_from_file

    ents = extract_from_file(tmp_path, m)
    inners = [e for e in ents if e.symbol_name == "inner"]
    assert len(inners) == 2
    assert inners[0].qualified_name != inners[1].qualified_name


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


@pytest.mark.asyncio
async def test_search_entities_substring(sample_repo: Path) -> None:
    from analysis.archaeology.extractor import extract_from_file
    from analysis.archaeology.graph_builder import collect_relations
    from analysis.archaeology.ids import stable_repo_id
    from analysis.archaeology.store import persist_archaeology_full, search_entities
    from database import init_database

    await init_database()
    repo_id = stable_repo_id(str(sample_repo.resolve()))
    commit = "c" * 40
    ents = extract_from_file(sample_repo, sample_repo / "pkg" / "mod.py")
    drafts = collect_relations(sample_repo, ents)
    await persist_archaeology_full(repo_id=repo_id, commit_sha=commit, entities=ents, drafts=drafts)

    by_sym = await search_entities(repo_id=repo_id, commit_sha=commit, query="inner", limit=20)
    assert any(e.symbol_name == "inner" for e in by_sym)

    by_file = await search_entities(repo_id=repo_id, commit_sha=commit, query="pkg/mod", limit=20)
    assert by_file

    by_kind = await search_entities(
        repo_id=repo_id, commit_sha=commit, query="C", entity_kind="class", limit=20
    )
    assert all(e.entity_kind == "class" for e in by_kind)
    assert any(e.symbol_name == "C" for e in by_kind)

    assert await search_entities(repo_id=repo_id, commit_sha=commit, query="   ", limit=5) == []


def test_analyze_resolve_smoke() -> None:
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
