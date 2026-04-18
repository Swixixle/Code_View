"""REST routes for analysis and evidence persistence."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from analysis.ingestion.materialize import (
    MaterializedSource,
    materialize_git_url,
    materialize_local_dir,
    materialize_zip_bytes,
    materialize_zip_url,
)
from analysis.ingestion.pipeline import AnalysisPipelineResult, run_analysis_pipeline
from analysis.civic_audit.endpoints import register_civic_audit_routes
from analysis.ingestion.platforms import resolve_netlify_repo_url, resolve_render_repo_url
from analysis.archaeology.history import git_file_history, git_log_line_range
from analysis.archaeology.project_impact import shallow_transitive_dependents
from analysis.archaeology.resolver import normalize_repo_relative_path, resolve_line_to_entity
from analysis.archaeology.store import list_child_entities, list_relations_for_entity
from analysis.archaeology.store import get_entity_by_id as get_code_entity
from analysis.evidence import AnalysisEngine
from models.db_models import EntityRelationRecord
from persistence.service import persistence_service

analysis_router = APIRouter()
_engine = AnalysisEngine()

register_civic_audit_routes(analysis_router)


class AnalyzeOptions(BaseModel):
    mode: str = Field("standard", description="quick | standard | deep")
    depth: str = Field("standard", description="Alias for mode")
    persist: bool = Field(True, description="Store results in SQLite")
    monitoring: bool = Field(False, description="Register repo in monitoring table")
    run_archaeology: bool = Field(
        True,
        description="Index Python entities (AST) and persist graph for tap queries",
    )


class AnalyzeRequest(AnalyzeOptions):
    source: str = Field(..., description="Git URL or local directory path")


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
    repo_id: str = ""
    archaeology: Optional[Dict[str, Any]] = None


class ResolveRequest(BaseModel):
    repo_id: str
    commit_sha: str
    file_path: str
    line: int = Field(..., ge=1)
    column: Optional[int] = Field(None, ge=0)


def _analyze_response_from_pipeline(pr: AnalysisPipelineResult, opts: AnalyzeOptions) -> AnalyzeResponse:
    r = pr.analysis
    return AnalyzeResponse(
        analysis_id=r.analysis_id,
        repository_url=r.repository_url,
        commit_hash=r.commit_hash,
        branch=r.branch,
        stages_completed=r.stages_completed,
        stages_failed=r.stages_failed,
        coverage_percentage=r.coverage_percentage,
        evidence_items=len(r.all_evidence),
        claims_assembled=len(r.claims),
        contradictions=len(r.contradictions),
        mechanisms=len(r.mechanisms),
        persisted=pr.persisted,
        monitoring_enabled=opts.monitoring,
        repo_id=pr.repo_id,
        archaeology=pr.archaeology,
    )


@analysis_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repo(body: AnalyzeRequest) -> AnalyzeResponse:
    """Clone (if URL) or use local path, run analysis, optionally persist."""
    source = body.source.strip()
    if not source:
        raise HTTPException(status_code=400, detail="source is required")

    mat: MaterializedSource | None = None
    try:
        if source.startswith("http://") or source.startswith("https://"):
            mat = await materialize_git_url(source)
            identity = source
        else:
            mat = materialize_local_dir(Path(source))
            identity = str(mat.path)

        pr = await run_analysis_pipeline(
            engine=_engine,
            repo_path=mat.path,
            source_for_identity=identity,
            persist=body.persist,
            monitoring=body.monitoring,
            monitoring_label=source,
            run_archaeology=body.run_archaeology,
        )
        return _analyze_response_from_pipeline(pr, body)
    finally:
        if mat and mat.cleanup:
            mat.cleanup()


# --- Universal ingestion (same engine + archaeology; platform APIs optional) ---


class RenderIngestRequest(AnalyzeOptions):
    service_id: str = Field(..., min_length=2)


class NetlifyIngestRequest(AnalyzeOptions):
    site_id: str = Field(..., min_length=2)


class ZipUrlIngestRequest(AnalyzeOptions):
    url: str = Field(..., min_length=8, description="http(s) URL to a .zip archive")


class ReplitIngestRequest(AnalyzeOptions):
    """Replit: no first-class public clone API here—use Repl git remote or an export zip URL."""

    zip_url: Optional[str] = None
    git_url: Optional[str] = None


class GitIngestRequest(AnalyzeOptions):
    repo_url: str = Field(..., min_length=8)


class LocalIngestRequest(AnalyzeOptions):
    directory_path: str = Field(..., min_length=1)


@analysis_router.get("/ingest/capabilities")
async def ingest_capabilities() -> Dict[str, Any]:
    return {
        "render_api": bool(os.environ.get("RENDER_API_KEY")),
        "netlify_api": bool(os.environ.get("NETLIFY_AUTH_TOKEN")),
        "note": "Archived uploads and git URLs work without host credentials.",
    }


@analysis_router.post("/ingest/archive", response_model=AnalyzeResponse)
async def ingest_uploaded_archive(
    file: UploadFile = File(...),
    persist: bool = Form(True),
    monitoring: bool = Form(False),
    run_archaeology: bool = Form(True),
    mode: str = Form("standard"),
    depth: str = Form("standard"),
) -> AnalyzeResponse:
    """Multipart upload of a .zip of source; same analysis as /analyze on a folder tree."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    label = f"upload:{file.filename or 'archive.zip'}"
    opts = AnalyzeOptions(
        persist=persist,
        monitoring=monitoring,
        run_archaeology=run_archaeology,
        mode=mode,
        depth=depth,
    )
    mat: MaterializedSource | None = None
    try:
        mat = materialize_zip_bytes(data, label)
        pr = await run_analysis_pipeline(
            engine=_engine,
            repo_path=mat.path,
            source_for_identity=label,
            persist=opts.persist,
            monitoring=opts.monitoring,
            monitoring_label=label,
            run_archaeology=opts.run_archaeology,
        )
        return _analyze_response_from_pipeline(pr, opts)
    finally:
        if mat and mat.cleanup:
            mat.cleanup()


@analysis_router.post("/ingest/zip-url", response_model=AnalyzeResponse)
async def ingest_zip_from_url(payload: ZipUrlIngestRequest) -> AnalyzeResponse:
    if not payload.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must be http(s)")
    label = f"zip-url:{payload.url[:180]}"
    mat = await materialize_zip_url(payload.url, label)
    try:
        pr = await run_analysis_pipeline(
            engine=_engine,
            repo_path=mat.path,
            source_for_identity=label,
            persist=payload.persist,
            monitoring=payload.monitoring,
            monitoring_label=label,
            run_archaeology=payload.run_archaeology,
        )
        return _analyze_response_from_pipeline(pr, payload)
    finally:
        if mat.cleanup:
            mat.cleanup()


@analysis_router.post("/ingest/render", response_model=AnalyzeResponse)
async def ingest_render(body: RenderIngestRequest) -> AnalyzeResponse:
    git_url, meta = await resolve_render_repo_url(body.service_id)
    if not git_url:
        raise HTTPException(status_code=501, detail=meta)
    label = f"render:{body.service_id}|{git_url}"
    mat = await materialize_git_url(git_url)
    try:
        pr = await run_analysis_pipeline(
            engine=_engine,
            repo_path=mat.path,
            source_for_identity=label,
            persist=body.persist,
            monitoring=body.monitoring,
            monitoring_label=f"render:{body.service_id}",
            run_archaeology=body.run_archaeology,
        )
        return _analyze_response_from_pipeline(pr, body)
    finally:
        if mat.cleanup:
            mat.cleanup()


@analysis_router.post("/ingest/netlify", response_model=AnalyzeResponse)
async def ingest_netlify(body: NetlifyIngestRequest) -> AnalyzeResponse:
    git_url, meta = await resolve_netlify_repo_url(body.site_id)
    if not git_url:
        raise HTTPException(status_code=501, detail=meta)
    label = f"netlify:{body.site_id}|{git_url}"
    mat = await materialize_git_url(git_url)
    try:
        pr = await run_analysis_pipeline(
            engine=_engine,
            repo_path=mat.path,
            source_for_identity=label,
            persist=body.persist,
            monitoring=body.monitoring,
            monitoring_label=f"netlify:{body.site_id}",
            run_archaeology=body.run_archaeology,
        )
        return _analyze_response_from_pipeline(pr, body)
    finally:
        if mat.cleanup:
            mat.cleanup()


@analysis_router.post("/ingest/replit", response_model=AnalyzeResponse)
async def ingest_replit(body: ReplitIngestRequest) -> AnalyzeResponse:
    mat: MaterializedSource | None = None
    try:
        if body.git_url and body.git_url.strip():
            u = body.git_url.strip()
            mat = await materialize_git_url(u)
            label = f"replit-git:{u[:200]}"
        elif body.zip_url and body.zip_url.strip():
            u = body.zip_url.strip()
            label = f"replit-zip:{u[:200]}"
            mat = await materialize_zip_url(u, label)
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide git_url (repl git remote) or zip_url (export download).",
            )
        pr = await run_analysis_pipeline(
            engine=_engine,
            repo_path=mat.path,
            source_for_identity=label,
            persist=body.persist,
            monitoring=body.monitoring,
            monitoring_label=label,
            run_archaeology=body.run_archaeology,
        )
        return _analyze_response_from_pipeline(pr, body)
    finally:
        if mat and mat.cleanup:
            mat.cleanup()


@analysis_router.post("/ingest/git", response_model=AnalyzeResponse)
async def ingest_git_alias(body: GitIngestRequest) -> AnalyzeResponse:
    u = body.repo_url.strip()
    if not u.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="repo_url must be an https git URL")
    mat = await materialize_git_url(u)
    try:
        pr = await run_analysis_pipeline(
            engine=_engine,
            repo_path=mat.path,
            source_for_identity=u,
            persist=body.persist,
            monitoring=body.monitoring,
            monitoring_label=u,
            run_archaeology=body.run_archaeology,
        )
        return _analyze_response_from_pipeline(pr, body)
    finally:
        if mat.cleanup:
            mat.cleanup()


@analysis_router.post("/ingest/local", response_model=AnalyzeResponse)
async def ingest_local_alias(body: LocalIngestRequest) -> AnalyzeResponse:
    mat = materialize_local_dir(Path(body.directory_path))
    pr = await run_analysis_pipeline(
        engine=_engine,
        repo_path=mat.path,
        source_for_identity=str(mat.path),
        persist=body.persist,
        monitoring=body.monitoring,
        monitoring_label=body.directory_path,
        run_archaeology=body.run_archaeology,
    )
    return _analyze_response_from_pipeline(pr, body)


@analysis_router.post("/resolve")
async def resolve_location(body: ResolveRequest) -> Dict[str, Any]:
    norm = normalize_repo_relative_path(body.file_path)
    res = await resolve_line_to_entity(
        repo_id=body.repo_id,
        commit_sha=body.commit_sha,
        file_path=norm,
        line=body.line,
        column=body.column,
    )
    if not res.ok or not res.primary:
        return {
            "repo_id": body.repo_id,
            "commit_sha": body.commit_sha,
            "file_path": norm,
            "line": body.line,
            "resolved_entity_id": None,
            "uncertainty": res.uncertainty
            or ["archaeological_gap"],
            "alternates": res.alternates,
        }
    p = res.primary
    return {
        "repo_id": body.repo_id,
        "commit_sha": body.commit_sha,
        "file_path": norm,
        "line": body.line,
        "resolved_entity_id": p["entity_id"],
        "entity_kind": p["entity_kind"],
        "symbol_name": p["symbol_name"],
        "qualified_name": p["qualified_name"],
        "span": {"start_line": p["start_line"], "end_line": p["end_line"]},
        "parent_chain": p.get("parent_chain", []),
        "confidence": p.get("confidence", "high"),
        "alternates": res.alternates,
        "uncertainty": res.uncertainty,
    }


@analysis_router.get("/entity/{entity_id}/identify")
async def entity_identify(entity_id: str) -> Dict[str, Any]:
    row = await get_code_entity(entity_id)
    if not row:
        raise HTTPException(status_code=404, detail="entity not found")
    children = await list_child_entities(entity_id)
    return {
        "repo_id": row.repo_id,
        "commit_sha": row.commit_sha,
        "entity_id": row.entity_id,
        "entity_kind": row.entity_kind,
        "symbol_name": row.symbol_name,
        "qualified_name": row.qualified_name,
        "file_path": row.file_path,
        "line_span": {"start_line": row.start_line, "end_line": row.end_line},
        "hashes": {
            "content_hash": row.content_hash,
            "signature_hash": row.signature_hash,
            "structural_hash": row.structural_hash,
        },
        "docstring": row.docstring,
        "direct_evidence": {
            "raw_content_preview": (row.raw_content[:2000] + "…")
            if row.raw_content and len(row.raw_content) > 2000
            else row.raw_content,
        },
        "parent_entity_id": row.parent_entity_id,
        "children_summary": [
            {
                "entity_id": c.entity_id,
                "entity_kind": c.entity_kind,
                "symbol_name": c.symbol_name,
                "line_span": {"start_line": c.start_line, "end_line": c.end_line},
            }
            for c in children[:50]
        ],
        "analysis_confidence": row.analysis_confidence,
    }


@analysis_router.get("/entity/{entity_id}/trace")
async def entity_trace(entity_id: str) -> Dict[str, Any]:
    row = await get_code_entity(entity_id)
    if not row:
        raise HTTPException(status_code=404, detail="entity not found")
    out, inc = await list_relations_for_entity(
        entity_id, repo_id=row.repo_id, commit_sha=row.commit_sha, direction="both"
    )

    def pack(rel: EntityRelationRecord, direction: str) -> Dict[str, Any]:
        other_id = rel.target_entity_id if direction == "out" else rel.source_entity_id
        return {
            "relation_id": rel.relation_id,
            "direction": direction,
            "relation_type": rel.relation_type,
            "confidence": rel.confidence,
            "peer_entity_id": other_id,
            "evidence": rel.evidence_json,
        }

    callers = [pack(r, "in") for r in inc if r.relation_type == "calls"]
    callees = [pack(r, "out") for r in out if r.relation_type == "calls"]
    imports_out = [pack(r, "out") for r in out if r.relation_type == "imports"]
    imported_by = [pack(r, "in") for r in inc if r.relation_type == "imports"]

    return {
        "repo_id": row.repo_id,
        "commit_sha": row.commit_sha,
        "entity_id": entity_id,
        "callers": callers,
        "callees": callees,
        "imports": imports_out,
        "imported_by": imported_by,
        "called_by": callers,
        "side_effect_hints": [],
        "graph_confidence_summary": {
            "calls_static": True,
            "note": "Dynamic dispatch and indirect calls are not modeled; empty lists may not imply absence.",
        },
    }


@analysis_router.get("/entity/{entity_id}/interpret")
async def entity_interpret(entity_id: str, repo_path: Optional[str] = None) -> Dict[str, Any]:
    row = await get_code_entity(entity_id)
    if not row:
        raise HTTPException(status_code=404, detail="entity not found")

    documented_intent: list[dict] = []
    if row.docstring:
        documented_intent.append(
            {
                "text": row.docstring,
                "source": "docstring",
                "file_path": row.file_path,
                "line_span": {"start_line": row.start_line, "end_line": row.end_line},
            }
        )

    observed: list[dict] = []
    gaps: list[str] = []
    arch_inf: list[dict] = []

    rp = Path(repo_path).expanduser().resolve() if repo_path else None
    if rp and rp.is_dir():
        rel = normalize_repo_relative_path(row.file_path)
        observed.extend(
            await git_log_line_range(
                rp, rel_file=rel, start_line=row.start_line, end_line=row.end_line
            )
        )
        if not observed:
            observed.extend(await git_file_history(rp, rel_file=rel))
    else:
        gaps.append(
            "No local repo_path provided; git log/blame not run. Pass ?repo_path=/abs/path for history-backed interpret."
        )

    if not observed and rp:
        gaps.append("No commits returned for this line range (thin history or non-git folder).")

    if not documented_intent and not observed:
        gaps.append("No clear design rationale found in available git history.")

    return {
        "repo_id": row.repo_id,
        "commit_sha": row.commit_sha,
        "entity_id": entity_id,
        "file_path": row.file_path,
        "line_span": {"start_line": row.start_line, "end_line": row.end_line},
        "documented_intent": documented_intent,
        "observed_evolution": observed,
        "architectural_inference": arch_inf,
        "archaeological_gaps": gaps,
    }


@analysis_router.get("/entity/{entity_id}/project")
async def entity_project(entity_id: str, max_depth: int = 2) -> Dict[str, Any]:
    row = await get_code_entity(entity_id)
    if not row:
        raise HTTPException(status_code=404, detail="entity not found")
    if max_depth < 1 or max_depth > 5:
        raise HTTPException(status_code=400, detail="max_depth must be between 1 and 5")

    direct: list[dict] = []
    _, inc = await list_relations_for_entity(
        entity_id, repo_id=row.repo_id, commit_sha=row.commit_sha, direction="in"
    )
    for rel in inc:
        if rel.relation_type not in ("calls", "imports"):
            continue
        peer_row = await get_code_entity(rel.source_entity_id)
        if peer_row:
            direct.append(
                {
                    "relation": "likely affected" if rel.relation_type == "calls" else "directly connected (imports)",
                    "entity_id": peer_row.entity_id,
                    "qualified_name": peer_row.qualified_name,
                    "file_path": peer_row.file_path,
                    "confidence": rel.confidence,
                }
            )

    _trans_ids, trans_meta = await shallow_transitive_dependents(
        entity_id=entity_id,
        repo_id=row.repo_id,
        commit_sha=row.commit_sha,
        max_depth=max_depth,
    )

    return {
        "repo_id": row.repo_id,
        "commit_sha": row.commit_sha,
        "entity_id": entity_id,
        "direct_dependents": direct,
        "transitive_dependents": trans_meta,
        "impacted_files": sorted({m["file_path"] for m in trans_meta}),
        "risk_notes": [
            "Shallow static reverse graph only; runtime-only edges are not visible.",
            "Treat impacted files as possibly affected, not guaranteed.",
        ],
        "confidence": "weak_impact_confidence" if not direct and not trans_meta else "low",
    }


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
