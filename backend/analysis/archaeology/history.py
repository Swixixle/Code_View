"""Git-first interpretation: blame + log; thin record => explicit gaps."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def git_blame_summary(
    repo_path: Path,
    *,
    rel_file: str,
    start_line: int,
    end_line: int,
    max_entries: int = 25,
) -> list[dict]:
    """Return recent unique blame rows for line range (best-effort)."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(repo_path),
        "blame",
        "-L",
        f"{start_line},{end_line}",
        "--porcelain",
        rel_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("git blame failed: %s", stderr.decode()[:300])
        return []

    entries: list[dict] = []
    seen: set[tuple[str, str]] = set()
    # porcelain: header lines then line content - simplified parse
    current_sha = ""
    for raw_line in stdout.decode(errors="replace").splitlines():
        if raw_line.startswith("\t"):
            continue
        if len(raw_line) >= 40 and raw_line[40] == " ":
            current_sha = raw_line[:40]
        if raw_line.startswith("author "):
            author = raw_line[len("author ") :].strip()
            if current_sha and (current_sha, author) not in seen:
                seen.add((current_sha, author))
                entries.append(
                    {
                        "commit_sha": current_sha,
                        "author_hint": author,
                        "source": "git_blame_porcelain",
                    }
                )
        if len(entries) >= max_entries:
            break
    return entries


async def git_log_line_range(
    repo_path: Path,
    *,
    rel_file: str,
    start_line: int,
    end_line: int,
    max_commits: int = 15,
) -> list[dict]:
    """git log -L (requires git 1.7.2+ line tracing). Returns [] if unsupported or non-git."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(repo_path),
        "log",
        f"-n{max_commits}",
        f"-L{start_line},{end_line}:{rel_file}",
        "--format=%H\t%an\t%ai\t%s",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.debug("git log -L failed (ok to fall back): %s", stderr.decode()[:200])
        return []
    out: list[dict] = []
    for ln in stdout.decode(errors="replace").splitlines():
        parts = ln.split("\t", 3)
        if len(parts) < 4:
            continue
        sha, author, authored_at, subj = parts[0], parts[1], parts[2], parts[3]
        out.append(
            {
                "commit_sha": sha.strip(),
                "author": author.strip(),
                "authored_at": authored_at.strip(),
                "subject": subj.strip(),
                "source": "git_log_line_range",
            }
        )
    return out


async def git_file_history(
    repo_path: Path,
    *,
    rel_file: str,
    max_commits: int = 12,
) -> list[dict]:
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(repo_path),
        "log",
        f"-n{max_commits}",
        "--format=%H%x09%s",
        "--",
        rel_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("git log failed: %s", stderr.decode()[:200])
        return []

    out: list[dict] = []
    for ln in stdout.decode(errors="replace").splitlines():
        if "\t" not in ln:
            continue
        sha, subj = ln.split("\t", 1)
        out.append(
            {
                "commit_sha": sha.strip(),
                "subject": subj.strip(),
                "source": "git_log_file",
            }
        )
    return out


def _tag_git_packet_entries(entries: list[dict], *, precision: str) -> None:
    """Mutate commit dicts with provenance fields for API / evidence alignment."""
    for d in entries:
        d["source_class"] = "git_history"
        d["provenance_label"] = "git history"
        d["derived_from_code"] = True
        d["derived_from_doc"] = False
        d["history_precision"] = precision


async def git_file_history_detailed(
    repo_path: Path,
    *,
    rel_file: str,
    max_commits: int = 12,
) -> list[dict]:
    """File-level log with author and date (best-effort; tabs in subject are rare)."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(repo_path),
        "log",
        f"-n{max_commits}",
        "--format=%H\t%an\t%ai\t%s",
        "--",
        rel_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("git log (detailed) failed: %s", stderr.decode()[:200])
        return []

    out: list[dict] = []
    for ln in stdout.decode(errors="replace").splitlines():
        parts = ln.split("\t", 3)
        if len(parts) < 4:
            continue
        sha, author, authored_at, subject = parts[0], parts[1], parts[2], parts[3]
        out.append(
            {
                "commit_sha": sha.strip(),
                "author": author.strip(),
                "authored_at": authored_at.strip(),
                "subject": subject.strip(),
                "source": "git_log_file",
            }
        )
    return out


async def entity_git_history_packet(
    repo_path: Path,
    *,
    rel_file: str,
    start_line: int,
    end_line: int,
    max_commits: int = 12,
) -> tuple[list[dict], str]:
    """
    Line-level log when `git log -L` works; otherwise file-level detailed log.
    Returns (annotated entries, precision) where precision is 'line' or 'file'.
    """
    line_log = await git_log_line_range(
        repo_path,
        rel_file=rel_file,
        start_line=start_line,
        end_line=end_line,
        max_commits=max_commits,
    )
    if line_log:
        for d in line_log:
            d.setdefault("author", "")
            d.setdefault("authored_at", "")
        _tag_git_packet_entries(line_log, precision="line")
        return line_log, "line"

    file_log = await git_file_history_detailed(repo_path, rel_file=rel_file, max_commits=max_commits)
    _tag_git_packet_entries(file_log, precision="file")
    return file_log, "file"
