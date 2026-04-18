"""Convert between Pydantic `AnalysisEvidence` and SQLAlchemy ORM rows."""

from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import (
    AnalysisRecord,
    ClaimRecord,
    ContradictionRecord,
    EvidenceRecord,
    MechanismRecord,
)
from models.evidence import (
    AnalysisEvidence,
    ClaimEvidence,
    Contradiction,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    ConfidenceLevel,
    ExtractedSymbol,
    MechanismTrace,
    SourceLocation,
)

def pydantic_to_orm(analysis_evidence: AnalysisEvidence, session: AsyncSession) -> AnalysisRecord:
    """Attach ORM graph for this analysis (caller commits)."""
    analysis_record = AnalysisRecord(
        id=analysis_evidence.analysis_id,
        repository_url=analysis_evidence.repository_url,
        commit_hash=analysis_evidence.commit_hash,
        branch=analysis_evidence.branch,
        analysis_started=analysis_evidence.analysis_started,
        analysis_completed=analysis_evidence.analysis_completed,
        analysis_duration=analysis_evidence.analysis_duration,
        stages_completed=analysis_evidence.stages_completed,
        stages_failed=analysis_evidence.stages_failed,
        coverage_percentage=analysis_evidence.coverage_percentage,
        monitoring_enabled=analysis_evidence.monitoring_enabled,
        next_check=analysis_evidence.next_check,
    )
    session.add(analysis_record)

    for evidence_item in analysis_evidence.all_evidence:
        session.add(
            EvidenceRecord(
                id=evidence_item.id,
                analysis_id=analysis_evidence.analysis_id,
                claim=evidence_item.claim,
                status=evidence_item.status.value,
                evidence_type=evidence_item.evidence_type.value,
                confidence=evidence_item.confidence.value,
                source_locations=[
                    {
                        "file_path": loc.file_path,
                        "line_start": loc.line_start,
                        "line_end": loc.line_end,
                        "column_start": loc.column_start,
                        "column_end": loc.column_end,
                    }
                    for loc in evidence_item.source_locations
                ],
                extracted_symbols=[
                    {
                        "name": sym.name,
                        "type": sym.type,
                        "location": {
                            "file_path": sym.location.file_path,
                            "line_start": sym.location.line_start,
                            "line_end": sym.location.line_end,
                            "column_start": sym.location.column_start,
                            "column_end": sym.location.column_end,
                        },
                        "signature": sym.signature,
                    }
                    for sym in evidence_item.extracted_symbols
                ],
                reasoning_chain=evidence_item.reasoning_chain,
                counterevidence=evidence_item.counterevidence,
                analysis_stage=evidence_item.analysis_stage,
                boundary_note=evidence_item.boundary_note,
                timestamp=evidence_item.timestamp,
                last_verified=evidence_item.last_verified,
            )
        )

    for claim in analysis_evidence.claims:
        session.add(
            ClaimRecord(
                id=claim.claim_id,
                analysis_id=analysis_evidence.analysis_id,
                claim_text=claim.claim_text,
                category=claim.category,
                overall_status=claim.overall_status.value,
                confidence_score=claim.confidence_score,
                last_assessed=claim.last_assessed,
                supporting_evidence_ids=[e.id for e in claim.supporting_evidence],
                contradicting_evidence_ids=[e.id for e in claim.contradicting_evidence],
            )
        )

    for contradiction in analysis_evidence.contradictions:
        session.add(
            ContradictionRecord(
                id=contradiction.contradiction_id,
                analysis_id=analysis_evidence.analysis_id,
                title=contradiction.title,
                description=contradiction.description,
                severity=contradiction.severity,
                claimed_behavior=contradiction.claimed_behavior,
                actual_behavior=contradiction.actual_behavior,
                evidence_for_claim=list(contradiction.evidence_for_claim),
                evidence_against_claim=list(contradiction.evidence_against_claim),
                affected_components=list(contradiction.affected_components),
                user_impact=contradiction.user_impact,
                security_impact=contradiction.security_impact,
                detected_at=contradiction.detected_at,
            )
        )

    for mechanism in analysis_evidence.mechanisms:
        session.add(
            MechanismRecord(
                id=str(uuid.uuid4()),
                analysis_id=analysis_evidence.analysis_id,
                claim_id=mechanism.claim_id,
                implementation_path=mechanism.implementation_path,
                entry_points=[
                    {
                        "name": ep.name,
                        "type": ep.type,
                        "location": {
                            "file_path": ep.location.file_path,
                            "line_start": ep.location.line_start,
                            "line_end": ep.location.line_end,
                            "column_start": ep.location.column_start,
                            "column_end": ep.location.column_end,
                        },
                        "signature": ep.signature,
                    }
                    for ep in mechanism.entry_points
                ],
                data_flow=mechanism.data_flow,
                dependencies=mechanism.dependencies,
            )
        )

    return analysis_record


def orm_to_pydantic(analysis_record: AnalysisRecord) -> AnalysisEvidence:
    """Rebuild `AnalysisEvidence` from a loaded `AnalysisRecord` (relationships populated)."""
    evidence_items: list[EvidenceItem] = []
    for er in analysis_record.evidence_items:
        source_locations: list[SourceLocation] = []
        if er.source_locations:
            for loc_data in er.source_locations:
                source_locations.append(SourceLocation(**loc_data))

        extracted_symbols: list[ExtractedSymbol] = []
        if er.extracted_symbols:
            for sym_data in er.extracted_symbols:
                loc = sym_data.get("location") or {}
                location = SourceLocation(
                    file_path=loc["file_path"],
                    line_start=loc["line_start"],
                    line_end=loc.get("line_end"),
                    column_start=loc.get("column_start"),
                    column_end=loc.get("column_end"),
                )
                extracted_symbols.append(
                    ExtractedSymbol(
                        name=sym_data["name"],
                        type=sym_data["type"],
                        location=location,
                        signature=sym_data.get("signature"),
                    )
                )

        evidence_items.append(
            EvidenceItem(
                id=er.id,
                claim=er.claim,
                status=EvidenceStatus(er.status),
                evidence_type=EvidenceType(er.evidence_type),
                confidence=ConfidenceLevel(er.confidence),
                source_locations=source_locations,
                extracted_symbols=extracted_symbols,
                reasoning_chain=er.reasoning_chain or [],
                counterevidence=er.counterevidence or [],
                analysis_stage=er.analysis_stage,
                boundary_note=er.boundary_note,
                timestamp=er.timestamp,
                last_verified=er.last_verified,
            )
        )

    by_id = {e.id: e for e in evidence_items}

    claims: list[ClaimEvidence] = []
    for cr in analysis_record.claims:
        supporting = [by_id[eid] for eid in (cr.supporting_evidence_ids or []) if eid in by_id]
        contradicting = [
            by_id[eid] for eid in (cr.contradicting_evidence_ids or []) if eid in by_id
        ]
        claims.append(
            ClaimEvidence(
                claim_id=cr.id,
                claim_text=cr.claim_text,
                category=cr.category,
                supporting_evidence=supporting,
                contradicting_evidence=contradicting,
                overall_status=EvidenceStatus(cr.overall_status),
                confidence_score=cr.confidence_score,
                last_assessed=cr.last_assessed,
            )
        )

    contradictions: list[Contradiction] = []
    for c in analysis_record.contradictions:
        contradictions.append(
            Contradiction(
                contradiction_id=c.id,
                title=c.title,
                description=c.description,
                severity=c.severity,
                claimed_behavior=c.claimed_behavior or "",
                actual_behavior=c.actual_behavior or "",
                evidence_for_claim=list(c.evidence_for_claim or []),
                evidence_against_claim=list(c.evidence_against_claim or []),
                affected_components=list(c.affected_components or []),
                user_impact=c.user_impact,
                security_impact=c.security_impact,
                detected_at=c.detected_at,
            )
        )

    mechanisms: list[MechanismTrace] = []
    for m in analysis_record.mechanisms:
        entry_points: list[ExtractedSymbol] = []
        for ep in m.entry_points or []:
            loc = ep.get("location") or {}
            entry_points.append(
                ExtractedSymbol(
                    name=ep["name"],
                    type=ep["type"],
                    location=SourceLocation(
                        file_path=loc["file_path"],
                        line_start=loc["line_start"],
                        line_end=loc.get("line_end"),
                        column_start=loc.get("column_start"),
                        column_end=loc.get("column_end"),
                    ),
                    signature=ep.get("signature"),
                )
            )
        mechanisms.append(
            MechanismTrace(
                claim_id=m.claim_id,
                implementation_path=m.implementation_path or [],
                entry_points=entry_points,
                data_flow=m.data_flow or [],
                dependencies=m.dependencies or [],
            )
        )

    return AnalysisEvidence(
        analysis_id=analysis_record.id,
        repository_url=analysis_record.repository_url,
        commit_hash=analysis_record.commit_hash,
        branch=analysis_record.branch,
        claims=claims,
        mechanisms=mechanisms,
        boundaries=[],
        contradictions=contradictions,
        all_evidence=evidence_items,
        analysis_started=analysis_record.analysis_started,
        analysis_completed=analysis_record.analysis_completed,
        analysis_duration=analysis_record.analysis_duration,
        stages_completed=analysis_record.stages_completed or [],
        stages_failed=analysis_record.stages_failed or [],
        coverage_percentage=analysis_record.coverage_percentage,
        monitoring_enabled=analysis_record.monitoring_enabled,
        next_check=analysis_record.next_check,
    )
