"""Stable repo_id and entity_id helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def stable_repo_id(repository_url_or_path: str) -> str:
    if repository_url_or_path.startswith(("http://", "https://")):
        normalized = repository_url_or_path.rstrip("/")
    else:
        normalized = Path(repository_url_or_path).expanduser().resolve().as_posix()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def make_entity_id(repo_id: str, commit_sha: str, qualified_name: str, file_path: str, start_line: int) -> str:
    raw = f"{repo_id}|{commit_sha}|{file_path}|{qualified_name}|{start_line}"
    return "ent_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def make_relation_id(repo_id: str, commit_sha: str, src: str, tgt: str, rel_type: str) -> str:
    raw = f"{repo_id}|{commit_sha}|{rel_type}|{src}|{tgt}"
    return "rel_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
