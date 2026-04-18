"""Normalize external code sources to a local directory for the analysis engine."""

from analysis.ingestion.materialize import MaterializedSource, materialize_local_dir
from analysis.ingestion.pipeline import run_analysis_pipeline

__all__ = ["MaterializedSource", "materialize_local_dir", "run_analysis_pipeline"]
