"""Safe extraction and tempdir lifecycle for universal ingestion."""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import httpx


@dataclass
class MaterializedSource:
    """A directory containing code to analyze."""

    path: Path
    """Absolute path to repository root (directory)."""

    source_label: str
    """String used for stable_repo_id and human-readable origin."""

    cleanup: Optional[Callable[[], None]]
    """If set, caller must invoke after analysis (typically deletes a temp dir)."""

    meta: dict
    """Non-secret provenance (e.g. platform, ids)."""


def _safe_extract_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for member in zf.infolist():
        if member.is_dir():
            continue
        name = member.filename.replace("\\", "/").lstrip("/")
        if not name or ".." in Path(name).parts:
            raise ValueError(f"Unsafe zip entry: {member.filename}")
        target = (dest / name).resolve()
        try:
            target.relative_to(dest)
        except ValueError as e:
            raise ValueError(f"Zip slip blocked: {member.filename}") from e
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member, "r") as src, open(target, "wb") as out:
            out.write(src.read())


def materialize_zip_bytes(data: bytes, source_label: str) -> MaterializedSource:
    root = Path(tempfile.mkdtemp(prefix="codeview_zip_"))

    def cleanup() -> None:
        import shutil

        shutil.rmtree(root, ignore_errors=True)

    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf, "r") as zf:
        _safe_extract_zip(zf, root)

    # If archive has a single top-level directory, use it as repo root (common for GitHub zips).
    children = [p for p in root.iterdir() if p.name not in ("__MACOSX",)]
    hidden_dirs = [p for p in children if p.is_dir() and not p.name.startswith(".")]
    repo_root = root
    if len(hidden_dirs) == 1 and not any(p.is_file() for p in children):
        repo_root = hidden_dirs[0]

    return MaterializedSource(
        path=repo_root.resolve(),
        source_label=source_label,
        cleanup=cleanup,
        meta={"kind": "zip_bytes"},
    )


async def materialize_zip_url(url: str, source_label: str, *, timeout: float = 120.0) -> MaterializedSource:
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        r = await client.get(url)
        r.raise_for_status()
        if len(r.content) > 500 * 1024 * 1024:
            raise ValueError("Archive too large (max ~500MB)")
        return materialize_zip_bytes(r.content, source_label)


def materialize_local_dir(path: Path, source_label: Optional[str] = None) -> MaterializedSource:
    p = path.expanduser().resolve()
    if not p.is_dir():
        raise ValueError("Local path must be a directory")
    label = source_label or str(p)
    return MaterializedSource(path=p, source_label=label, cleanup=None, meta={"kind": "local"})


async def git_shallow_clone(repo_url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        "git",
        "clone",
        "--depth",
        "1",
        repo_url,
        str(dest),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode(errors="replace")[:2000])


async def materialize_git_url(repo_url: str) -> MaterializedSource:
    root = Path(tempfile.mkdtemp(prefix="codeview_git_"))
    repo_path = root / "repo"

    def cleanup() -> None:
        import shutil

        shutil.rmtree(root, ignore_errors=True)

    await git_shallow_clone(repo_url, repo_path)
    return MaterializedSource(
        path=repo_path.resolve(),
        source_label=repo_url.strip(),
        cleanup=cleanup,
        meta={"kind": "git_clone"},
    )
