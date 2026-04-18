"""Register `POST /civic-audit` on the analysis API router."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from analysis.civic_audit.analyzer import CivicAuditAnalyzer
from analysis.civic_audit.scorecard import generate_civic_scorecard_markdown


class CivicAuditRequest(BaseModel):
    directory_path: str = Field(..., description="Absolute path to repository root on disk")
    focus_areas: List[str] = Field(
        default_factory=lambda: ["all"],
        description="Reserved for future filtering (currently all stages run)",
    )
    include_scorecard: bool = True
    adversarial_testing: bool = True


class CivicAuditResponse(BaseModel):
    audit_id: str
    repo_path: str
    findings_count: int
    critical_findings: int
    overall_civic_score: float
    corruption_detection_score: float
    temporal_integrity_score: float
    cryptographic_robustness_score: float
    transparency_score: float
    pattern_rules_found: List[str]
    signing_flows_detected: int
    recommendations: List[str]
    attack_vectors_identified: int
    scorecard_markdown: Optional[str] = None
    methodology_note: str = Field(
        default="Heuristic scan only; not a penetration test or institutional audit.",
        description="Uncertainty framing",
    )


def register_civic_audit_routes(router: APIRouter) -> None:
    @router.post("/civic-audit", response_model=CivicAuditResponse)
    async def run_civic_audit(request: CivicAuditRequest) -> CivicAuditResponse:
        repo_path = Path(request.directory_path).expanduser().resolve()
        if not repo_path.is_dir():
            raise HTTPException(status_code=400, detail="Invalid directory path")

        analyzer = CivicAuditAnalyzer()
        result = await analyzer.analyze_civic_accountability(repo_path)

        critical_count = sum(1 for f in result.findings if f.severity == "critical")
        recommendations = list({f.recommendation for f in result.findings if f.recommendation})
        attack_vectors = sum(1 for f in result.findings if f.attack_vector)

        scorecard: Optional[str] = None
        if request.include_scorecard:
            scorecard = generate_civic_scorecard_markdown(result)

        return CivicAuditResponse(
            audit_id=f"civic_{uuid.uuid4().hex[:12]}",
            repo_path=str(repo_path),
            findings_count=len(result.findings),
            critical_findings=critical_count,
            overall_civic_score=result.overall_civic_score,
            corruption_detection_score=result.corruption_detection_score,
            temporal_integrity_score=result.temporal_integrity_score,
            cryptographic_robustness_score=result.cryptographic_robustness_score,
            transparency_score=result.transparency_score,
            pattern_rules_found=list(dict.fromkeys(result.pattern_rules_found)),
            signing_flows_detected=len(result.signing_flows),
            recommendations=recommendations[:10],
            attack_vectors_identified=attack_vectors,
            scorecard_markdown=scorecard,
        )
