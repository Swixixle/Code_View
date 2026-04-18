"""REST routes for analysis and evidence persistence."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from analysis.evidence import AnalysisEngine
from persistence.service import persistence_service

analysis_router = APIRouter()
_engine = AnalysisEngine()


class AnalyzeRequest(BaseModel):
    source: str = Field(..., description="Git URL or local directory path")
    mode: str = Field("standard", description="quick | standard | deep")
    depth: str = Field("standard", description="Alias for mode")
    persist: bool = Field(True, description="Store results in SQLite")
    monitoring: bool = Field(False, description="Register repo in monitoring table")


class AnalyzeResponse(BaseModel):
    analysis_id: str
    repository_url: str
    commit_hash: str
    branch: str
    stages_completed: List[str]
    stages_failed: List[str] = []
    coverage_percentage: float
    evidence_items: int = 0
    claims_assembled: int = 0
    contradictions: int = 0
    mechanisms: int = 0
    persisted: bool = False
    monitoring_enabled: bool = False


@analysis_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repo(body: AnalyzeRequest) -> AnalyzeResponse:
    """Clone (if URL) or use local path, run analysis, optionally persist."""
    source = body.source.strip()
    if not source:
        raise HTTPException(status_code=400, detail="source is required")

    persisted = False

    if source.startswith("http://") or source.startswith("https://"):
        with tempfile.TemporaryDirectory() as tmp:
            repo_path = Path(tmp) / "repo"
            proc = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                "--depth",
                "1",
                source,
                str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"git clone failed: {stderr.decode()[:500]}",
                )
            result = await _engine.analyze_codebase(repo_path, source)
    else:
        path = Path(source).expanduser().resolve()
        if not path.is_dir():
            raise HTTPException(status_code=400, detail="Local path must be a directory")
        result = await _engine.analyze_codebase(path, str(path))

    if body.persist:
        persisted = await persistence_service.store_analysis(result)

    if body.monitoring:
        await persistence_service.set_repository_monitoring(source, enabled=True)

    return AnalyzeResponse(
        analysis_id=result.analysis_id,
        repository_url=result.repository_url,
        commit_hash=result.commit_hash,
        branch=result.branch,
        stages_completed=result.stages_completed,
        stages_failed=result.stages_failed,
        coverage_percentage=result.coverage_percentage,
        evidence_items=len(result.all_evidence),
        claims_assembled=len(result.claims),
        contradictions=len(result.contradictions),
        mechanisms=len(result.mechanisms),
        persisted=persisted and body.persist,
        monitoring_enabled=body.monitoring,
    )


@analysis_router.get("/analyses")
async def list_analyses(repository_url: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    if limit > 100:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 100")
    analyses = await persistence_service.list_analyses(repository_url, limit)
    return {
        "analyses": analyses,
        "count": len(analyses),
        "repository_filter": repository_url,
    }


@analysis_router.get("/evidence/search")
async def search_evidence(
    query: str,
    analysis_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    if len(query) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")
    if limit > 100:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 100")
    items = await persistence_service.search_evidence(query, analysis_id, limit)
    return {
        "evidence": items,
        "count": len(items),
        "query": query,
        "analysis_filter": analysis_id,
    }


@analysis_router.get("/evidence/{evidence_id}")
async def get_evidence_item(evidence_id: str) -> Dict[str, Any]:
    evidence = await persistence_service.get_evidence_item(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return evidence


@analysis_router.post("/monitoring/repository")
async def set_repository_monitoring(request: dict) -> Dict[str, Any]:
    repository_url = request.get("repository_url")
    if not repository_url:
        raise HTTPException(status_code=400, detail="Repository URL required")
    check_interval = request.get("check_interval", 300)
    enabled = request.get("enabled", True)
    if check_interval < 60:
        raise HTTPException(status_code=400, detail="Check interval must be at least 60 seconds")
    ok = await persistence_service.set_repository_monitoring(repository_url, check_interval, enabled)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to configure monitoring")
    return {
        "repository_url": repository_url,
        "check_interval": check_interval,
        "enabled": enabled,
        "status": "configured",
    }


@analysis_router.get("/monitoring/repository")
async def get_repository_monitoring(repository_url: str) -> Dict[str, Any]:
    data = await persistence_service.get_repository_monitoring(repository_url)
    if not data:
        raise HTTPException(status_code=404, detail="Repository not monitored")
    return data


async def _analysis_stats_payload() -> Dict[str, Any]:
    recent = await persistence_service.list_analyses(limit=100)
    total = len(recent)
    completed = len([a for a in recent if a.get("analysis_completed")])
    total_evidence = sum(a.get("evidence_count", 0) for a in recent)
    total_contradictions = sum(a.get("contradictions_count", 0) for a in recent)
    repos = list({a["repository_url"] for a in recent})
    return {
        "total_analyses": total,
        "completed_analyses": completed,
        "total_evidence_items": total_evidence,
        "total_contradictions": total_contradictions,
        "unique_repositories": len(repos),
        "average_evidence_per_analysis": total_evidence / total if total else 0,
        "completion_rate": completed / total if total else 0,
    }


@analysis_router.get("/stats")
@analysis_router.get("/stats/summary")
async def get_analysis_stats() -> Dict[str, Any]:
    return await _analysis_stats_payload()


@analysis_router.get("/{analysis_id}/summary")
async def get_analysis_summary(analysis_id: str) -> Dict[str, Any]:
    summary = await persistence_service.get_analysis_summary(analysis_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Analysis not found: {analysis_id}")
    return summary


@analysis_router.get("/{analysis_id}")
async def get_analysis_full(analysis_id: str) -> Dict[str, Any]:
    analysis = await persistence_service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis not found: {analysis_id}")

    return {
        "analysis_id": analysis.analysis_id,
        "repository_url": analysis.repository_url,
        "commit_hash": analysis.commit_hash,
        "branch": analysis.branch,
        "analysis_started": analysis.analysis_started.isoformat(),
        "analysis_completed": analysis.analysis_completed.isoformat()
        if analysis.analysis_completed
        else None,
        "analysis_duration": analysis.analysis_duration,
        "stages_completed": analysis.stages_completed,
        "stages_failed": analysis.stages_failed,
        "coverage_percentage": analysis.coverage_percentage,
        "evidence_items": [
            {
                "id": item.id,
                "claim": item.claim,
                "status": item.status.value,
                "confidence": item.confidence.value,
                "evidence_type": item.evidence_type.value,
                "source_locations": [
                    {
                        "file_path": loc.file_path,
                        "line_start": loc.line_start,
                        "line_end": loc.line_end,
                    }
                    for loc in item.source_locations
                ],
                "analysis_stage": item.analysis_stage,
                "reasoning_chain": item.reasoning_chain,
            }
            for item in analysis.all_evidence
        ],
        "claims": [
            {
                "id": claim.claim_id,
                "claim_text": claim.claim_text,
                "category": claim.category,
                "overall_status": claim.overall_status.value,
                "confidence_score": claim.confidence_score,
                "supporting_evidence_count": len(claim.supporting_evidence),
                "contradicting_evidence_count": len(claim.contradicting_evidence),
            }
            for claim in analysis.claims
        ],
        "contradictions": len(analysis.contradictions),
        "mechanisms": len(analysis.mechanisms),
    }


@analysis_router.delete("/{analysis_id}")
async def delete_analysis(analysis_id: str) -> Dict[str, str]:
    raise HTTPException(status_code=501, detail="Analysis deletion not implemented yet")
