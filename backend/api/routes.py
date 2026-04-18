"""REST routes for analysis."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from analysis.evidence import AnalysisEngine

analysis_router = APIRouter()
_engine = AnalysisEngine()


class AnalyzeRequest(BaseModel):
    source: str = Field(..., description="Git URL or local path")
    mode: str = Field("standard", description="quick | standard | deep")
    depth: str = Field("standard", description="Alias for mode")


class AnalyzeResponse(BaseModel):
    analysis_id: str
    repository_url: str
    commit_hash: str
    branch: str
    stages_completed: List[str]
    coverage_percentage: float


@analysis_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repo(body: AnalyzeRequest) -> AnalyzeResponse:
    """Clone (if URL) and run the analysis engine."""
    source = body.source.strip()
    if not source:
        raise HTTPException(status_code=400, detail="source is required")

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

    return AnalyzeResponse(
        analysis_id=result.analysis_id,
        repository_url=result.repository_url,
        commit_hash=result.commit_hash,
        branch=result.branch,
        stages_completed=result.stages_completed,
        coverage_percentage=result.coverage_percentage,
    )


@analysis_router.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str) -> Dict[str, Any]:
    """Placeholder until persistence is wired; returns 404 for unknown IDs."""
    raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
