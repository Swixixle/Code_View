"""Provenance fields, doc demotion, and evidence search ranking."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from models.evidence import (
    SOURCE_CLASS_DOCUMENTATION_CLAIM,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    source_class_rank,
)
from persistence.service import EvidencePersistenceService


def test_source_class_rank_orders_code_before_docs() -> None:
    assert source_class_rank("code_definition") < source_class_rank(SOURCE_CLASS_DOCUMENTATION_CLAIM)


def test_evidence_item_provenance_defaults() -> None:
    item = EvidenceItem(
        claim="x",
        status=EvidenceStatus.UNKNOWN,
        evidence_type=EvidenceType.EXTRACTED,
        confidence=ConfidenceLevel.LOW,
        analysis_stage="t",
    )
    assert item.source_class == "keyword_heuristic"
    assert item.support_strength == "weak"


def test_evidence_item_pydantic_round_trip() -> None:
    item = EvidenceItem(
        claim="c",
        status=EvidenceStatus.UNKNOWN,
        evidence_type=EvidenceType.EXTRACTED,
        confidence=ConfidenceLevel.LOW,
        analysis_stage="t",
        source_class="documentation_claim",
        linked_entity_ids=["e1"],
        linked_relation_ids=["r1"],
        support_strength="moderate",
        derived_from_doc=True,
        derived_from_code=False,
    )
    restored = EvidenceItem.model_validate(item.model_dump())
    assert restored.source_class == item.source_class
    assert restored.linked_entity_ids == ["e1"]
    assert restored.derived_from_doc is True


def test_doc_claim_demotion(tmp_path: Path) -> None:
    from analysis.claims_enhanced import extract_enhanced_claims

    (tmp_path / "README.md").write_text(
        "This project implements Ed25519 signing and full verification for all payloads.\n",
        encoding="utf-8",
    )
    items = extract_enhanced_claims(tmp_path)
    assert items
    docish = [e for e in items if e.source_class == "documentation_claim"]
    assert docish, "expected documentation_claim classification"
    assert all(e.derived_from_doc for e in docish)
    assert not any(e.derived_from_code for e in docish)
    assert all(e.refinement_signal == "doc_only_claim" for e in docish)
    assert all(e.confidence.value != "high" for e in docish)


def test_python_parser_marks_code_definition(tmp_path: Path) -> None:
    from analysis.parsers.python_parser_enhanced import parse_python_directory_enhanced

    (tmp_path / "signing.py").write_text(
        "def sign_payload(b: bytes) -> bytes:\n    return b\n",
        encoding="utf-8",
    )
    ev = parse_python_directory_enhanced(tmp_path)
    defs = [e for e in ev if e.source_class == "code_definition"]
    assert defs, "expected at least one code_definition from AST"


def test_search_evidence_sorts_by_source_class() -> None:
    from sqlalchemy import delete

    from database import get_session, init_database
    from models.db_models import AnalysisRecord, EvidenceRecord

    async def _run() -> None:
        await init_database()
        aid = "test_provenance_sort_analysis"
        async with get_session() as session:
            await session.execute(delete(EvidenceRecord).where(EvidenceRecord.analysis_id == aid))
            await session.execute(delete(AnalysisRecord).where(AnalysisRecord.id == aid))
            session.add(
                AnalysisRecord(
                    id=aid,
                    repository_url="https://example.com/r",
                    commit_hash="abc",
                    branch="main",
                    analysis_started=datetime.now(timezone.utc),
                    coverage_percentage=0.0,
                )
            )
            ts_old = datetime(2020, 1, 1, tzinfo=timezone.utc)
            ts_new = datetime(2024, 1, 1, tzinfo=timezone.utc)
            session.add(
                EvidenceRecord(
                    id="ev_doc",
                    analysis_id=aid,
                    claim="signing and verification described in README",
                    status="unknown",
                    evidence_type="extracted",
                    confidence="low",
                    analysis_stage="cryptographic_claims_extraction",
                    timestamp=ts_new,
                    last_verified=ts_new,
                    source_class="documentation_claim",
                    derived_from_doc=True,
                    derived_from_code=False,
                    support_strength="weak",
                )
            )
            session.add(
                EvidenceRecord(
                    id="ev_code",
                    analysis_id=aid,
                    claim="signing function implements payload handling",
                    status="supported",
                    evidence_type="extracted",
                    confidence="high",
                    analysis_stage="python_ast_parsing",
                    timestamp=ts_old,
                    last_verified=ts_old,
                    source_class="code_definition",
                    derived_from_doc=False,
                    derived_from_code=True,
                    support_strength="strong",
                )
            )
            await session.commit()

        svc = EvidencePersistenceService()
        out = await svc.search_evidence("signing", analysis_id=aid, limit=10)
        assert [x["id"] for x in out][:2] == ["ev_code", "ev_doc"]

        async with get_session() as session:
            await session.execute(delete(EvidenceRecord).where(EvidenceRecord.analysis_id == aid))
            await session.execute(delete(AnalysisRecord).where(AnalysisRecord.id == aid))
            await session.commit()

    asyncio.run(_run())
