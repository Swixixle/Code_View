"""Regression test for cross-module call resolution in archaeology static graph.

Bug receipt: docs/receipts/sweeps_relief_sign_bytes_grep.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analysis.archaeology.extractor import extract_repository
from analysis.archaeology.graph_builder import collect_relations

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "cross_module_calls"


def _collect(bundle_root: Path):
    bundle = extract_repository(bundle_root)
    return collect_relations(bundle_root, bundle.entities), bundle.entities


def test_sign_bytes_has_three_direct_callers() -> None:
    """Three modules call sign_bytes; subpkg __init__ re-exports only — not a call edge."""
    drafts, _ents = _collect(FIXTURE_ROOT)
    target = "sweeps_relief_fixture.signer.sign_bytes"
    callers = {d.source_qual for d in drafts if d.relation_type == "calls" and d.target_qual == target}
    assert "sweeps_relief_fixture.logger.log_event" in callers
    assert "sweeps_relief_fixture.policy.build_policy" in callers
    assert "sweeps_relief_fixture.subpkg.consumer.consume" in callers
    assert len(callers) == 3
    init_call = any(
        d.source_qual == "sweeps_relief_fixture.subpkg" and d.relation_type == "calls" and d.target_qual == target
        for d in drafts
    )
    assert not init_call


def test_trace_resolves_absolute_import() -> None:
    """Absolute `from pkg.mod import name` must produce a call edge."""
    drafts, _ = _collect(FIXTURE_ROOT)
    logger_tr = [
        d
        for d in drafts
        if d.relation_type == "calls"
        and d.source_qual == "sweeps_relief_fixture.logger.log_event"
        and "sign_bytes" in (d.target_qual or "")
    ]
    assert logger_tr
    assert any(d.target_qual == "sweeps_relief_fixture.signer.sign_bytes" for d in logger_tr)


def test_trace_resolves_relative_import() -> None:
    """Relative `from .mod import name` must produce a call edge."""
    drafts, _ = _collect(FIXTURE_ROOT)
    pol = [
        d
        for d in drafts
        if d.relation_type == "calls"
        and d.source_qual == "sweeps_relief_fixture.policy.build_policy"
    ]
    assert any(d.target_qual == "sweeps_relief_fixture.signer.sign_bytes" for d in pol)


def test_trace_resolves_through_reexport() -> None:
    """Import via re-exported subpackage must resolve to defining sign_bytes."""
    drafts, _ = _collect(FIXTURE_ROOT)
    cons = [
        d
        for d in drafts
        if d.relation_type == "calls"
        and d.source_qual == "sweeps_relief_fixture.subpkg.consumer.consume"
    ]
    assert any(d.target_qual == "sweeps_relief_fixture.signer.sign_bytes" for d in cons)
