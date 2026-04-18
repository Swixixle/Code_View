"""
Scheduled monitoring: repository polling, re-analysis, WebSocket notifications.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from analysis.evidence import AnalysisEngine
from api.websocket import WebSocketManager
from models.evidence import AnalysisEvidence, EvidenceTimeline

logger = logging.getLogger(__name__)


class RepositoryMonitor:
    """Monitors repository changes and triggers re-analysis."""

    def __init__(self, ws_manager: WebSocketManager) -> None:
        self.ws_manager = ws_manager
        self.monitored_repos: Dict[str, Dict[str, Any]] = {}
        self.analysis_engine = AnalysisEngine()

    async def add_repository(self, repo_url: str, check_interval: int = 300) -> None:
        self.monitored_repos[repo_url] = {
            "url": repo_url,
            "last_check": datetime.now(),
            "last_commit": None,
            "check_interval": check_interval,
            "analysis_timeline": EvidenceTimeline(repository_url=repo_url),
        }

        await self.analyze_repository(repo_url)
        logger.info("Added repository to monitoring: %s", repo_url)

    async def check_for_changes(self) -> None:
        for repo_url, repo_data in list(self.monitored_repos.items()):
            try:
                if self._should_check_repo(repo_data):
                    await self._check_repository_changes(repo_url, repo_data)
            except Exception as e:  # noqa: BLE001
                logger.error("Error checking repository %s: %s", repo_url, e)

    def _should_check_repo(self, repo_data: Dict[str, Any]) -> bool:
        last_check: datetime = repo_data["last_check"]
        interval: int = repo_data["check_interval"]
        return datetime.now() - last_check > timedelta(seconds=interval)

    async def _check_repository_changes(self, repo_url: str, repo_data: Dict[str, Any]) -> None:
        latest_commit = await self._get_latest_commit(repo_url)

        if latest_commit != repo_data["last_commit"]:
            logger.info("Changes detected in %s: %s", repo_url, latest_commit)

            await self.ws_manager.broadcast_to_subscribers(
                repo_url,
                {
                    "type": "repository_change",
                    "repository": repo_url,
                    "new_commit": latest_commit,
                    "old_commit": repo_data["last_commit"],
                    "timestamp": datetime.now().isoformat(),
                },
            )

            await self.analyze_repository(repo_url)

            repo_data["last_commit"] = latest_commit
            repo_data["last_check"] = datetime.now()

    async def _get_latest_commit(self, repo_url: str) -> str:
        try:
            if "github.com" in repo_url:
                return await self._get_github_latest_commit(repo_url)
            return await self._get_git_latest_commit(repo_url)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to get latest commit for %s: %s", repo_url, e)
            return ""

    async def _get_github_latest_commit(self, repo_url: str) -> str:
        parts = repo_url.replace("https://github.com/", "").split("/")
        owner, repo = parts[0], parts[1].replace(".git", "")
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/HEAD"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return str(data["sha"])
                raise RuntimeError(f"GitHub API error: {response.status}")

    async def _get_git_latest_commit(self, repo_url: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "git",
            "ls-remote",
            repo_url,
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            line = stdout.decode().strip().split()
            return line[0] if line else ""
        raise RuntimeError(stderr.decode())

    async def analyze_repository(self, repo_url: str) -> None:
        try:
            await self.ws_manager.broadcast_to_subscribers(
                repo_url,
                {
                    "type": "analysis_started",
                    "repository": repo_url,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = Path(temp_dir) / "repo"
                process = await asyncio.create_subprocess_exec(
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    repo_url,
                    str(repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.communicate()

                if process.returncode != 0:
                    raise RuntimeError("Failed to clone repository")

                analysis_result = await self.analysis_engine.analyze_codebase(repo_path, repo_url)

                repo_data = self.monitored_repos[repo_url]
                timeline: EvidenceTimeline = repo_data["analysis_timeline"]
                timeline.add_analysis(analysis_result)

                regressions = timeline.detect_regressions()
                if regressions:
                    await self._notify_regressions(repo_url, regressions)

                await self.ws_manager.broadcast_to_subscribers(
                    repo_url,
                    {
                        "type": "analysis_completed",
                        "repository": repo_url,
                        "analysis_id": analysis_result.analysis_id,
                        "claims_count": len(analysis_result.claims),
                        "contradictions_count": len(analysis_result.contradictions),
                        "regressions": regressions,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                logger.info("Analysis completed for %s", repo_url)

        except Exception as e:  # noqa: BLE001
            logger.error("Analysis failed for %s: %s", repo_url, e)
            await self.ws_manager.broadcast_to_subscribers(
                repo_url,
                {
                    "type": "analysis_failed",
                    "repository": repo_url,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def _notify_regressions(self, repo_url: str, regressions: List[Dict[str, Any]]) -> None:
        await self.ws_manager.broadcast_to_subscribers(
            repo_url,
            {
                "type": "regressions_detected",
                "repository": repo_url,
                "regressions": regressions,
                "severity": "high" if len(regressions) > 5 else "medium",
                "timestamp": datetime.now().isoformat(),
            },
        )

    def get_repository_status(self, repo_url: str) -> Optional[Dict[str, Any]]:
        if repo_url not in self.monitored_repos:
            return None

        repo_data = self.monitored_repos[repo_url]
        timeline: EvidenceTimeline = repo_data["analysis_timeline"]

        latest_analysis: Optional[AnalysisEvidence] = (
            timeline.evidence_history[-1] if timeline.evidence_history else None
        )

        return {
            "url": repo_url,
            "monitoring": True,
            "last_check": repo_data["last_check"].isoformat(),
            "last_commit": repo_data["last_commit"],
            "check_interval": repo_data["check_interval"],
            "analysis_count": len(timeline.evidence_history),
            "latest_analysis": {
                "id": latest_analysis.analysis_id,
                "timestamp": latest_analysis.analysis_started.isoformat(),
                "claims": len(latest_analysis.claims),
                "contradictions": len(latest_analysis.contradictions),
            }
            if latest_analysis
            else None,
        }


class AnalysisScheduler:
    """Coordinates monitoring and analysis scheduling."""

    def __init__(self, ws_manager: WebSocketManager) -> None:
        self.ws_manager = ws_manager
        self.repository_monitor = RepositoryMonitor(ws_manager)
        self.pending_tasks: List[Dict[str, Any]] = []

    async def process_pending_tasks(self) -> None:
        if not self.pending_tasks:
            return

        current_tasks = self.pending_tasks.copy()
        self.pending_tasks.clear()

        for task in current_tasks:
            try:
                if task["type"] == "analyze_repository":
                    await self.repository_monitor.analyze_repository(task["repo_url"])
                elif task["type"] == "add_monitoring":
                    await self.repository_monitor.add_repository(
                        task["repo_url"],
                        task.get("interval", 300),
                    )
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to process task %s: %s", task, e)

    async def check_repository_changes(self) -> None:
        await self.repository_monitor.check_for_changes()

    def schedule_analysis(self, repo_url: str) -> None:
        self.pending_tasks.append(
            {
                "type": "analyze_repository",
                "repo_url": repo_url,
                "scheduled_at": datetime.now(),
            }
        )

    def schedule_monitoring(self, repo_url: str, interval: int = 300) -> None:
        self.pending_tasks.append(
            {
                "type": "add_monitoring",
                "repo_url": repo_url,
                "interval": interval,
                "scheduled_at": datetime.now(),
            }
        )
