"""Regression tests for civic audit heuristics (real extractor + temp repos)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from analysis.civic_audit.analyzer import CivicAuditAnalyzer, CivicAuditResult


def _run_audit(repo: Path) -> CivicAuditResult:
    return asyncio.run(CivicAuditAnalyzer().analyze_civic_accountability(repo))


def test_civic_audit_empty_repo(tmp_path: Path) -> None:
    result = _run_audit(tmp_path)
    assert result.repo_path == str(tmp_path.resolve())
    assert result.duration_seconds is not None
    assert 0 <= result.duration_seconds < 30.0
    assert any(f.category == "methodology" for f in result.findings)
    for name in (
        "corruption_detection_score",
        "temporal_integrity_score",
        "cryptographic_robustness_score",
        "transparency_score",
        "overall_civic_score",
    ):
        v = getattr(result, name)
        assert isinstance(v, float)
        assert 0.0 <= v <= 1.0


def test_civic_audit_detects_patterns_and_crypto(tmp_path: Path) -> None:
    (tmp_path / "pattern_engine.py").write_text(
        "def soft_bundle_v1(donations, vote_date):\n"
        "    threshold = 50000\n"
        "    return True\n"
        "def sector_convergence_v1(donations):\n"
        "    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "signing.py").write_text(
        "# Module handles signing / verification of receipts (fixture keywords).\n"
        "def sign(x):\n"
        "    import random\n"
        "    return random.random()\n"
        "def verify(x):\n"
        "    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "temporal_analysis.py").write_text(
        "# proximity timeline sequence before after during overlap gap interval\n"
        "def f():\n"
        "    from datetime import datetime\n"
        "    return datetime.now()\n",
        encoding="utf-8",
    )

    result = _run_audit(tmp_path)
    assert "SOFT_BUNDLE_V1" in result.pattern_rules_found
    assert "SECTOR_CONVERGENCE_V1" in result.pattern_rules_found
    assert len(result.signing_flows) >= 1
    assert len(result.temporal_logic) >= 1
    titles = {f.title for f in result.findings}
    assert any("threshold" in t.lower() for t in titles)
    assert any("random" in t.lower() for t in titles)


def test_calculate_civic_scores_bounds() -> None:
    analyzer = CivicAuditAnalyzer()
    result = CivicAuditResult(repo_path="/tmp")
    result.pattern_rules_found = ["SOFT_BUNDLE_V1"]
    result.temporal_logic = [{"file": "a.py", "indicators": 3}]
    result.signing_flows = [{"file": "s.py", "type": "signing", "algorithms": []}]
    analyzer._calculate_civic_scores(result)
    assert 0.0 <= result.overall_civic_score <= 1.0
