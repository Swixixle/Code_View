"""
Code View - Core Evidence Model
Evidence-first architecture with full provenance tracking
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
import uuid


class EvidenceType(str, Enum):
    EXTRACTED = "extracted"
    OBSERVED = "observed"
    INFERRED = "inferred"
    HEURISTIC = "heuristic"
    NOT_VERIFIED = "not_verified"


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceLocation(BaseModel):
    """Exact source reference for evidence."""

    file_path: str
    line_start: int
    line_end: Optional[int] = None
    column_start: Optional[int] = None
    column_end: Optional[int] = None


class ExtractedSymbol(BaseModel):
    """Code symbol referenced in evidence."""

    name: str
    type: str
    location: SourceLocation
    signature: Optional[str] = None


class EvidenceItem(BaseModel):
    """Individual piece of evidence with full provenance."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim: str
    status: EvidenceStatus
    evidence_type: EvidenceType
    confidence: ConfidenceLevel

    source_locations: List[SourceLocation] = Field(default_factory=list)
    extracted_symbols: List[ExtractedSymbol] = Field(default_factory=list)
    reasoning_chain: List[str] = Field(default_factory=list)
    counterevidence: List[str] = Field(default_factory=list)

    analysis_stage: str
    boundary_note: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    last_verified: datetime = Field(default_factory=datetime.now)

    depends_on: List[str] = Field(default_factory=list)
    supports: List[str] = Field(default_factory=list)


class ClaimEvidence(BaseModel):
    """A claim and its supporting/contradicting evidence."""

    claim_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_text: str
    category: str

    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    contradicting_evidence: List[EvidenceItem] = Field(default_factory=list)

    overall_status: EvidenceStatus
    confidence_score: float
    last_assessed: datetime = Field(default_factory=datetime.now)


class MechanismTrace(BaseModel):
    """How a claim is actually implemented."""

    claim_id: str
    implementation_path: List[str]
    entry_points: List[ExtractedSymbol]
    data_flow: List[Dict[str, Any]]
    dependencies: List[str]


class TrustBoundary(BaseModel):
    """Where system justification stops."""

    boundary_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    boundary_type: str

    signed_fields: List[str] = Field(default_factory=list)
    unsigned_fields: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)

    risk_level: str
    potential_issues: List[str] = Field(default_factory=list)


class Contradiction(BaseModel):
    """Detected gap between claims and reality."""

    contradiction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    severity: str

    claimed_behavior: str
    actual_behavior: str
    evidence_for_claim: List[str] = Field(default_factory=list)
    evidence_against_claim: List[str] = Field(default_factory=list)

    affected_components: List[str] = Field(default_factory=list)
    user_impact: Optional[str] = None
    security_impact: Optional[str] = None

    detected_at: datetime = Field(default_factory=datetime.now)


class AnalysisEvidence(BaseModel):
    """Complete evidence package for a codebase analysis."""

    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository_url: str
    commit_hash: str
    branch: str

    claims: List[ClaimEvidence] = Field(default_factory=list)
    mechanisms: List[MechanismTrace] = Field(default_factory=list)
    boundaries: List[TrustBoundary] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)

    all_evidence: List[EvidenceItem] = Field(default_factory=list)

    analysis_started: datetime = Field(default_factory=datetime.now)
    analysis_completed: Optional[datetime] = None
    analysis_duration: Optional[float] = None

    stages_completed: List[str] = Field(default_factory=list)
    stages_failed: List[str] = Field(default_factory=list)
    coverage_percentage: float = 0.0

    monitoring_enabled: bool = False
    next_check: Optional[datetime] = None


# Primary aggregate used across API and storage
EvidenceModel = AnalysisEvidence


class EvidenceTimeline(BaseModel):
    """Historical tracking of evidence changes."""

    repository_url: str
    evidence_history: List[AnalysisEvidence] = Field(default_factory=list)

    def add_analysis(self, analysis: AnalysisEvidence) -> None:
        self.evidence_history.append(analysis)
        self.evidence_history.sort(key=lambda x: x.analysis_started)

    def get_evidence_evolution(self, claim_text: str) -> List[Dict[str, Any]]:
        evolution = []
        for analysis in self.evidence_history:
            for claim in analysis.claims:
                if claim.claim_text == claim_text:
                    evolution.append(
                        {
                            "timestamp": analysis.analysis_started,
                            "commit": analysis.commit_hash,
                            "status": claim.overall_status,
                            "confidence": claim.confidence_score,
                        }
                    )
        return evolution

    def detect_regressions(self) -> List[Dict[str, Any]]:
        if len(self.evidence_history) < 2:
            return []

        current = self.evidence_history[-1]
        previous = self.evidence_history[-2]

        regressions = []

        current_claims = {c.claim_text: c for c in current.claims}
        previous_claims = {c.claim_text: c for c in previous.claims}

        for claim_text, current_claim in current_claims.items():
            if claim_text in previous_claims:
                prev_claim = previous_claims[claim_text]
                if current_claim.confidence_score < prev_claim.confidence_score - 0.1:
                    regressions.append(
                        {
                            "type": "confidence_degradation",
                            "claim": claim_text,
                            "old_confidence": prev_claim.confidence_score,
                            "new_confidence": current_claim.confidence_score,
                            "commit": current.commit_hash,
                        }
                    )

        return regressions


def create_evidence_from_source(
    claim: str,
    file_path: str,
    line_start: int,
    symbol_name: str,
    symbol_type: str,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    reasoning: Optional[List[str]] = None,
) -> EvidenceItem:
    return EvidenceItem(
        claim=claim,
        status=EvidenceStatus.SUPPORTED,
        evidence_type=EvidenceType.EXTRACTED,
        confidence=confidence,
        source_locations=[SourceLocation(file_path=file_path, line_start=line_start)],
        extracted_symbols=[
            ExtractedSymbol(
                name=symbol_name,
                type=symbol_type,
                location=SourceLocation(file_path=file_path, line_start=line_start),
            )
        ],
        reasoning_chain=reasoning or [f"Found {symbol_type} '{symbol_name}' in {file_path}"],
        analysis_stage="symbol_extraction",
    )


def merge_evidence_items(items: List[EvidenceItem]) -> EvidenceItem:
    if not items:
        raise ValueError("Cannot merge empty evidence list")

    base = items[0].model_copy(deep=True)
    for item in items[1:]:
        base.source_locations.extend(item.source_locations)
        base.extracted_symbols.extend(item.extracted_symbols)
        base.reasoning_chain.extend(item.reasoning_chain)
        base.counterevidence.extend(item.counterevidence)

    if len(items) >= 3 and all(item.confidence == ConfidenceLevel.HIGH for item in items):
        base.confidence = ConfidenceLevel.HIGH

    return base
