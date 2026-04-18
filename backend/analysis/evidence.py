"""High-level analysis engine producing `AnalysisEvidence`."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.evidence import AnalysisEvidence

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """Runs ingestion and symbol-level passes; MVP returns a minimal evidence bundle."""

    async def analyze_codebase(self, repo_path: Path, repo_url: str) -> AnalysisEvidence:
        started = datetime.now()
        commit_hash = await self._read_head_commit(repo_path)
        branch = await self._read_branch(repo_path)

        # Placeholder: full pipeline (parsers, extractors) plugs in here.
        result = AnalysisEvidence(
            repository_url=repo_url,
            commit_hash=commit_hash or "unknown",
            branch=branch or "unknown",
            analysis_started=started,
            analysis_completed=datetime.now(),
            stages_completed=["ingestion", "symbol_extraction_stub"],
            coverage_percentage=0.0,
        )
        result.analysis_duration = (
            (result.analysis_completed - result.analysis_started).total_seconds()
            if result.analysis_completed
            else None
        )
        logger.info("Analysis stub finished for %s @ %s", repo_url, commit_hash)
        return result

    async def _read_head_commit(self, repo_path: Path) -> Optional[str]:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(repo_path),
            "rev-parse",
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        return stdout.decode().strip() or None

    async def _read_branch(self, repo_path: Path) -> Optional[str]:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(repo_path),
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        return stdout.decode().strip() or None
