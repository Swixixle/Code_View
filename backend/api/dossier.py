"""Educational forensic dossier generation (Markdown download)."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Response

from analysis.educational_dossier import (
    generate_comparative_educational_dossier,
    generate_educational_dossier,
)
from analysis.evidence import AnalysisEngine
from persistence.service import persistence_service

logger = logging.getLogger(__name__)

dossier_router = APIRouter()
_engine = AnalysisEngine()


def _sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:120]


@dossier_router.get("/report/{analysis_id}")
async def get_educational_dossier_from_store(
    analysis_id: str,
    educational: bool = True,
    format: str = "markdown",
) -> Response:
    """Generate a Markdown dossier from a persisted analysis."""
    analysis = await persistence_service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis not found: {analysis_id}")

    if format.lower() != "markdown":
        raise HTTPException(status_code=400, detail="Only markdown format is supported")

    try:
        dossier_content = generate_educational_dossier(analysis, educational)
        filename = _sanitize_filename(f"forensic_dossier_{analysis_id}.md")
        return Response(
            content=dossier_content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Dossier generation failed")
        raise HTTPException(status_code=500, detail=f"Dossier generation failed: {e}") from e


@dossier_router.post("/analyze-with-dossier")
async def analyze_with_educational_dossier(
    request: Dict[str, Any],
    educational: bool = True,
    format: str = "markdown",
) -> Response:
    """Run analysis and return a Markdown dossier (optionally persist first)."""
    source = (request.get("source") or "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="Source repository required")

    persist = request.get("persist", True)

    if format.lower() != "markdown":
        raise HTTPException(status_code=400, detail="Only markdown format is supported")

    try:
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
                analysis = await _engine.analyze_codebase(repo_path, source)
        else:
            repo_path = Path(source).expanduser().resolve()
            if not repo_path.is_dir():
                raise HTTPException(status_code=400, detail="Local directory not found")
            analysis = await _engine.analyze_codebase(repo_path, str(repo_path))

        if persist:
            ok = await persistence_service.store_analysis(analysis)
            if not ok:
                raise HTTPException(status_code=500, detail="Failed to persist analysis")

        dossier_content = generate_educational_dossier(analysis, educational)
        repo_name = source.rstrip("/").split("/")[-1].replace(".git", "") or "repository"
        filename = _sanitize_filename(f"{repo_name}_forensic_dossier.md")

        return Response(
            content=dossier_content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("Analysis with dossier failed")
        raise HTTPException(status_code=500, detail=f"Analysis with dossier failed: {e}") from e


@dossier_router.post("/comparative-dossier")
async def comparative_educational_dossier(
    request: Dict[str, Any],
    educational: bool = True,
    format: str = "markdown",
) -> Response:
    """Clone and analyze multiple repositories; return one comparative Markdown dossier."""
    repositories: List[str] = request.get("repositories") or []
    if len(repositories) < 2:
        raise HTTPException(status_code=400, detail="At least 2 repositories required")
    if len(repositories) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 repositories allowed")

    if format.lower() != "markdown":
        raise HTTPException(status_code=400, detail="Only markdown format is supported")

    analyses = []
    errors: List[str] = []

    for repo_url in repositories:
        url = (repo_url or "").strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            errors.append(f"Skip non-HTTP URL: {url}")
            continue
        try:
            with tempfile.TemporaryDirectory() as tmp:
                repo_path = Path(tmp) / "repo"
                proc = await asyncio.create_subprocess_exec(
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    url,
                    str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                if proc.returncode != 0:
                    errors.append(f"{url}: {stderr.decode()[:200]}")
                    continue
                analysis = await _engine.analyze_codebase(repo_path, url)
                analyses.append(analysis)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{url}: {e}")

    if not analyses:
        msg = "No repositories could be analyzed"
        if errors:
            msg += ": " + "; ".join(errors)
        raise HTTPException(status_code=400, detail=msg)

    try:
        body = generate_comparative_educational_dossier(analyses, educational)
        if errors:
            body += "\n\n## Clone / analysis notes\n\n" + "\n".join(f"- {e}" for e in errors)

        filename = _sanitize_filename(f"comparative_forensic_dossier_{len(analyses)}_repos.md")
        return Response(
            content=body,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Comparative dossier failed")
        raise HTTPException(status_code=500, detail=f"Comparative dossier generation failed: {e}") from e
