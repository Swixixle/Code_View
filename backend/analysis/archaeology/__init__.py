"""Entity-centric code archaeology (Python AST index + static graph)."""

from analysis.archaeology.ids import stable_repo_id
from analysis.archaeology.service import ingest_repository

__all__ = ["ingest_repository", "stable_repo_id"]
