"""Resolve git-backed source URLs from host platform APIs (optional credentials)."""

from __future__ import annotations

import os
from typing import Any

import httpx


def _pick_str(*candidates: Any) -> str | None:
    for c in candidates:
        if isinstance(c, str) and (c.startswith("http://") or c.startswith("https://") or c.startswith("git@")):
            return c
    return None


async def resolve_render_repo_url(service_id: str) -> tuple[str | None, dict[str, Any]]:
    """
    GET https://api.render.com/v1/services/{serviceId}
    Expects RENDER_API_KEY in environment.
    """
    token = os.environ.get("RENDER_API_KEY", "").strip()
    if not token:
        return None, {
            "configured": False,
            "uncertainty": ["archaeological_gap"],
            "detail": "Set RENDER_API_KEY to enable Render ingestion.",
        }

    url = f"https://api.render.com/v1/services/{service_id}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        raw = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code >= 400:
            return None, {
                "configured": True,
                "http_status": r.status_code,
                "detail": raw if isinstance(raw, dict) else r.text[:500],
            }

    data = raw if isinstance(raw, dict) else {}
    if isinstance(data.get("service"), dict):
        data = data["service"]
    # Service object may expose repo at top-level or nested.
    repo = data.get("repo")
    git_url: str | None = None
    if isinstance(repo, str):
        git_url = _pick_str(repo)
    elif isinstance(repo, dict):
        git_url = _pick_str(
            repo.get("url"),
            repo.get("repo"),
            repo.get("cloneUrl"),
        )
    if not git_url:
        git_url = _pick_str(
            data.get("repoUrl"),
            data.get("repositoryUrl"),
        )

    if not git_url:
        return None, {
            "configured": True,
            "detail": "Render service has no linked git URL in API response (manual git URL may be required).",
            "keys_sample": list(data.keys())[:30],
        }
    return git_url, {"configured": True, "platform": "render", "service_id": service_id}


async def resolve_netlify_repo_url(site_id: str) -> tuple[str | None, dict[str, Any]]:
    """
    GET https://api.netlify.com/api/v1/sites/{site_id}
    Expects NETLIFY_AUTH_TOKEN (personal access token).
    """
    token = os.environ.get("NETLIFY_AUTH_TOKEN", "").strip()
    if not token:
        return None, {
            "configured": False,
            "uncertainty": ["archaeological_gap"],
            "detail": "Set NETLIFY_AUTH_TOKEN to enable Netlify ingestion.",
        }

    url = f"https://api.netlify.com/api/v1/sites/{site_id}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        try:
            data = r.json()
        except Exception:  # noqa: BLE001
            data = {}
        if r.status_code >= 400:
            return None, {"configured": True, "http_status": r.status_code, "detail": data}

    if not isinstance(data, dict):
        return None, {"configured": True, "detail": "Unexpected Netlify response"}

    build = data.get("build_settings") or {}
    git_url = _pick_str(
        build.get("repo_url"),
        build.get("repoUrl"),
        data.get("repo_url"),
    )
    if not git_url:
        return None, {
            "configured": True,
            "detail": "Netlify site has no linked git repo_url in build_settings (connect repo in Netlify or pass git URL).",
            "site_name": data.get("name"),
        }
    return git_url, {"configured": True, "platform": "netlify", "site_id": site_id}
