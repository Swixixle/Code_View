"""Monitoring and live-feed related HTTP routes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Request

monitoring_router = APIRouter()


def _scheduler(request: Request):
    return request.app.state.scheduler


@monitoring_router.get("/status")
async def monitoring_status(request: Request) -> Dict[str, Any]:
    """Scheduler presence check (detailed repo status via future endpoints)."""
    sched = _scheduler(request)
    return {
        "scheduler": "active" if sched else "missing",
        "pending_tasks": len(sched.pending_tasks) if sched else 0,
    }


@monitoring_router.get("/repository")
async def repository_status(request: Request, url: str) -> Optional[Dict[str, Any]]:
    sched = _scheduler(request)
    if not sched:
        return None
    return sched.repository_monitor.get_repository_status(url)
