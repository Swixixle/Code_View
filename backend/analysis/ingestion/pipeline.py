"""Shared analysis + archaeology path used by /analyze and universal ingest."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from analysis.archaeology.ids import stable_repo_id
from analysis.archaeology.service import ingest_repository
from analysis.evidence import AnalysisEngine
from models.evidence import AnalysisEvidence
from persistence.service import persistence_service


@dataclass
class AnalysisPipelineResult:
    analysis: AnalysisEvidence
    repo_id: str
    archaeology: Optional[Dict[str, Any]]
    persisted: bool


async def run_analysis_pipeline(
    *,
    engine: AnalysisEngine,
    repo_path: Path,
    source_for_identity: str,
    persist: bool,
    monitoring: bool,
    monitoring_label: str,
    run_archaeology: bool,
) -> AnalysisPipelineResult:
    """
    Run evidence analysis + optional archaeology index.
    `source_for_identity` must be stable for a given origin (URL, path, or platform label).
    """
    repo_id = stable_repo_id(source_for_identity)
    result = await engine.analyze_codebase(repo_path, source_for_identity)

    archaeology: Dict[str, Any] | None = None
    if run_archaeology and result.commit_hash not in ("unknown", ""):
        archaeology = await ingest_repository(repo_path, repo_id=repo_id, commit_sha=result.commit_hash)
    else:
        archaeology = {
            "skipped": True,
            "reason": "no_git_commit" if result.commit_hash in ("unknown", "") else "archaeology_disabled",
        }

    persisted = False
    if persist:
        persisted = await persistence_service.store_analysis(result)

    if monitoring:
        await persistence_service.set_repository_monitoring(monitoring_label, enabled=True)

    return AnalysisPipelineResult(
        analysis=result,
        repo_id=repo_id,
        archaeology=archaeology,
        persisted=persisted,
    )
