# Civic audit extension (heuristic)

Integrated modules:

- `analysis/civic_audit/analyzer.py` — `CivicAuditAnalyzer`
- `analysis/civic_audit/endpoints.py` — registers `POST /api/analysis/civic-audit`
- `analysis/civic_audit/scorecard.py` — optional Markdown scorecard in API response
- `backend/civic_audit_cli.py` — terminal helper

**Important:** Outputs are **triage heuristics** (keywords, AST slices, filename hints), not a formal security audit or democratic certification.

## API

```bash
curl -s -X POST http://localhost:8000/api/analysis/civic-audit \
  -H "Content-Type: application/json" \
  -d '{"directory_path": "/absolute/path/to/repo", "include_scorecard": true}'
```

JSON response includes `scorecard_markdown` when `include_scorecard` is true.

## CLI

```bash
cd backend
.venv/bin/python civic_audit_cli.py /absolute/path/to/repo
```

Writes `civic_audit_<dirname>.md` next to the repo’s parent directory (same behavior as typical one-off reports).
