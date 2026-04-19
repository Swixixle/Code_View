"""
SQLAlchemy ORM models for persisted analysis evidence (SQLite).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    repository_url: Mapped[str] = mapped_column(String, nullable=False)
    commit_hash: Mapped[str] = mapped_column(String, nullable=False)
    branch: Mapped[str] = mapped_column(String, nullable=False)

    analysis_started: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    analysis_completed: Mapped[datetime | None] = mapped_column(DateTime)
    analysis_duration: Mapped[float | None] = mapped_column(Float)

    stages_completed: Mapped[list | None] = mapped_column(JSON)
    stages_failed: Mapped[list | None] = mapped_column(JSON)
    coverage_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    next_check: Mapped[datetime | None] = mapped_column(DateTime)

    refinement_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    evidence_items: Mapped[list["EvidenceRecord"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    claims: Mapped[list["ClaimRecord"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    contradictions: Mapped[list["ContradictionRecord"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    mechanisms: Mapped[list["MechanismRecord"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    claim: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)

    source_locations: Mapped[list | None] = mapped_column(JSON)
    extracted_symbols: Mapped[list | None] = mapped_column(JSON)
    reasoning_chain: Mapped[list | None] = mapped_column(JSON)
    counterevidence: Mapped[list | None] = mapped_column(JSON)

    analysis_stage: Mapped[str] = mapped_column(String, nullable=False)
    boundary_note: Mapped[str | None] = mapped_column(Text)
    refinement_signal: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_verified: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source_class: Mapped[str] = mapped_column(String, nullable=False, default="keyword_heuristic")
    linked_entity_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    linked_relation_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    support_strength: Mapped[str] = mapped_column(String, nullable=False, default="weak")
    derived_from_doc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    derived_from_code: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    analysis: Mapped["AnalysisRecord"] = relationship(back_populates="evidence_items")


class ClaimRecord(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    overall_status: Mapped[str] = mapped_column(String, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    last_assessed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    supporting_evidence_ids: Mapped[list | None] = mapped_column(JSON)
    contradicting_evidence_ids: Mapped[list | None] = mapped_column(JSON)

    analysis: Mapped["AnalysisRecord"] = relationship(back_populates="claims")


class ContradictionRecord(Base):
    __tablename__ = "contradictions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)

    claimed_behavior: Mapped[str | None] = mapped_column(Text)
    actual_behavior: Mapped[str | None] = mapped_column(Text)
    evidence_for_claim: Mapped[list | None] = mapped_column(JSON)
    evidence_against_claim: Mapped[list | None] = mapped_column(JSON)

    affected_components: Mapped[list | None] = mapped_column(JSON)
    user_impact: Mapped[str | None] = mapped_column(Text)
    security_impact: Mapped[str | None] = mapped_column(Text)

    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    analysis: Mapped["AnalysisRecord"] = relationship(back_populates="contradictions")


class MechanismRecord(Base):
    __tablename__ = "mechanisms"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("analysis_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    claim_id: Mapped[str] = mapped_column(String, nullable=False)
    implementation_path: Mapped[list | None] = mapped_column(JSON)
    entry_points: Mapped[list | None] = mapped_column(JSON)
    data_flow: Mapped[list | None] = mapped_column(JSON)
    dependencies: Mapped[list | None] = mapped_column(JSON)

    analysis: Mapped["AnalysisRecord"] = relationship(back_populates="mechanisms")


class RepositoryMonitorRecord(Base):
    __tablename__ = "repository_monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_url: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    last_check: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_commit: Mapped[str | None] = mapped_column(String)
    check_interval: Mapped[int] = mapped_column(Integer, default=300)

    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CodeEntityRecord(Base):
    """Indexed Python (etc.) symbols for archaeology queries."""

    __tablename__ = "code_entities"

    entity_id: Mapped[str] = mapped_column(String, primary_key=True)
    repo_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    commit_sha: Mapped[str] = mapped_column(String, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String, nullable=False, default="python")
    entity_kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    symbol_name: Mapped[str] = mapped_column(String, nullable=False)
    qualified_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_entity_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    signature_hash: Mapped[str] = mapped_column(String, nullable=False)
    structural_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at_analysis: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_commit: Mapped[str] = mapped_column(String, nullable=False)
    analysis_confidence: Mapped[str] = mapped_column(String, nullable=False, default="high")
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)


class EntityRelationRecord(Base):
    """Edges between entities (contains, calls, imports, ancestry hints)."""

    __tablename__ = "entity_relations"

    relation_id: Mapped[str] = mapped_column(String, primary_key=True)
    repo_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    commit_sha: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    discovered_at_commit: Mapped[str] = mapped_column(String, nullable=False)
    created_at_analysis: Mapped[datetime] = mapped_column(DateTime, nullable=False)
