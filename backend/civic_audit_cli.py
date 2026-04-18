#!/usr/bin/env python3
"""CLI: run civic heuristic audit on a local directory."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


async def _main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python civic_audit_cli.py /path/to/repo", file=sys.stderr)
        raise SystemExit(2)
    repo = Path(sys.argv[1]).expanduser().resolve()
    if not repo.is_dir():
        print(f"Error: not a directory: {repo}", file=sys.stderr)
        raise SystemExit(1)

    from analysis.civic_audit.analyzer import CivicAuditAnalyzer
    from analysis.civic_audit.scorecard import generate_civic_scorecard_markdown

    analyzer = CivicAuditAnalyzer()
    result = await analyzer.analyze_civic_accountability(repo)

    print(f"Findings: {len(result.findings)}")
    print(f"Critical: {sum(1 for f in result.findings if f.severity == 'critical')}")
    print(f"Overall (heuristic): {result.overall_civic_score:.2f}")

    out = repo.parent / f"civic_audit_{repo.name}.md"
    out.write_text(generate_civic_scorecard_markdown(result), encoding="utf-8")
    print(f"Wrote: {out}")


if __name__ == "__main__":
    asyncio.run(_main())
