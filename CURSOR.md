# Code View — developer guide (Cursor / AI-assisted work)

This file is optimized for **implementation work**: where code lives, how imports resolve, and how to extend the system safely. User-oriented docs: **`CODE_VIEW_README.md`**. Broader specs: **`CODE_VIEW_SPEC.md`**, **`CODE_VIEW_STRUCTURE.md`**.

Python import paths assume **`backend/` is the working directory** (same as running uvicorn from `backend/`).

---

## Quick start

```bash
# Backend (use a venv)
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Frontend
cd frontend
npm install
npm run dev
```

API docs: `http://localhost:8000/docs`  
CORS allows `http://localhost:3000` (see `backend/main.py`).

### One-shot local analysis (verify API)

```bash
curl -s -X POST http://localhost:8000/api/analysis/ingest/local \
  -H "Content-Type: application/json" \
  -d '{"directory_path": "/absolute/path/to/repo", "persist": true, "run_archaeology": true}'
```

Use a real absolute path on your machine.

---

## Repository layout (backend)

```
backend/
├── main.py                 # FastAPI app, lifespan, /ws/live-feed
├── database.py             # Async SQLAlchemy, SQLite path → ../data/code_view.db (from repo root)
├── api/
│   ├── routes.py           # /api/analysis/* (analyze, ingest/*, resolve, entity/*)
│   ├── dossier.py          # /api/dossier/*
│   └── monitoring.py
├── analysis/
│   ├── evidence.py        # AnalysisEngine — main pipeline orchestration
│   ├── archaeology/       # entity extraction, graph, resolver, store, history
│   ├── ingestion/        # materialize (zip/git), pipeline, platforms (Render/Netlify)
│   ├── parsers/          # python_parser*.py
│   └── refinement/        # dedup, classifiers, refinement entry
├── models/
│   ├── evidence.py        # Pydantic: EvidenceItem, AnalysisEvidence, …
│   └── db_models.py       # SQLAlchemy: AnalysisRecord, EvidenceRecord, CodeEntityRecord, …
├── persistence/
│   └── service.py         # store/get analysis
└── tests/
    └── test_archaeology.py
```

---

## Entry points and imports

### `AnalysisEngine`

```python
from pathlib import Path
from analysis.evidence import AnalysisEngine

engine = AnalysisEngine()
analysis = await engine.analyze_codebase(Path("/abs/path/to/repo"), "label-for-metadata")
# analysis: models.evidence.AnalysisEvidence
```

### Full pipeline (evidence + SQLite archaeology + optional persist)

```python
from pathlib import Path
from analysis.evidence import AnalysisEngine
from analysis.ingestion.pipeline import run_analysis_pipeline

engine = AnalysisEngine()
pr = await run_analysis_pipeline(
    engine=engine,
    repo_path=Path("/abs/path/to/repo"),
    source_for_identity="stable-string-for-repo-id",
    persist=True,
    monitoring=False,
    monitoring_label="same-as-user-facing-source-if-needed",
    run_archaeology=True,
)
# pr.analysis, pr.repo_id, pr.archaeology (dict or None), pr.persisted
```

### Archaeology only (already have a tree + commit SHA)

```python
from analysis.archaeology.service import ingest_repository

stats = await ingest_repository(
    Path("/abs/path/to/repo"),
    repo_id="from stable_repo_id(...)",
    commit_sha="40-char-git-sha",
)
```

### Database init (tests or scripts)

```python
import asyncio
from database import init_database

asyncio.run(init_database())
```

SQLite file: **`Code_View/data/code_view.db`** (directory next to `backend/`). Not configured via `.env` in-tree today (`database.py` holds the URL).

---

## Key models (don’t confuse layers)

| Layer | Location | Role |
|--------|----------|------|
| **`EvidenceItem`** | `models/evidence.py` | Pydantic; in-memory evidence rows |
| **`CodeEntityRecord`** | `models/db_models.py` | SQLAlchemy persistence for entities |
| **`ExtractedEntity`** | `analysis/archaeology/extractor.py` | Dataclass during AST extraction before insert |

`EvidenceItem` (abbreviated):

```python
# models/evidence.py — EvidenceItem
# Fields include: claim, status, evidence_type, confidence,
# source_locations, analysis_stage, refinement_signal, …
```

Static graph edges (v1): **`contains`**, **`imports`**, **`calls`** — see `analysis/archaeology/graph_builder.py` (no generic `inherits` edge today).

---

## HTTP API (prefix `/api`)

| Area | Methods | Notes |
|------|---------|--------|
| Ingest | `GET /api/analysis/ingest/capabilities` | Which platform env vars are set |
| | `POST /api/analysis/ingest/{archive,zip-url,git,local,render,netlify,replit}` | JSON bodies extend shared analyze options (see `routes.py`) |
| Legacy | `POST /api/analysis/analyze` | `{"source": "<git url or local path>"}` |
| Archaeology | `POST /api/analysis/resolve` | JSON: `repo_id`, `commit_sha`, `file_path`, `line` |
| | `GET /api/analysis/entity/{id}/{identify,trace,interpret,project}` | `interpret` optional `?repo_path=` |
| Civic (heuristic) | `POST /api/analysis/civic-audit` | Local `directory_path` only; see `analysis/civic_audit/` |
| Dossier | `POST /api/dossier/analyze-with-dossier` | Not `/educational` |
| | `POST /api/dossier/comparative-dossier` | 2–5 HTTPS repo URLs |
| | `GET /api/dossier/report/{analysis_id}` | |
| WS | `WS /ws/live-feed` | Heartbeat / subscribe |

Full routes live in `backend/api/routes.py` and `backend/api/dossier.py`. Routers mount under **`/api/analysis`** and **`/api/dossier`** in `main.py`.

---

## Testing

```bash
cd backend
.venv/bin/python -m pytest tests/ -q
```

Focused: `pytest tests/test_archaeology.py`.

---

## Extension recipes

**New Python evidence pattern:**  
`analysis/parsers/python_parser_enhanced.py` (or `python_parser.py`), then wire through `analysis/evidence.py` / refinement if volume spikes.

**New ingest source:**  
`analysis/ingestion/materialize.py`, optional `platforms.py`, new route in `api/routes.py`, extend `GET .../ingest/capabilities` if needed.

**Archaeology:**  
`analysis/archaeology/extractor.py`, `graph_builder.py`, `store.py`, `resolver.py`.

---

## What not to assume

- **Crypto / “trust” language** in output is **heuristic** (patterns + doc text), not a formal audit.  
- **Self-analysis metrics** (counts, timing) vary by tree and README text; see **`docs/code_view_self_analysis.md`** for how to read a run.  
- **Platform ingest** (Render/Netlify) resolves **linked git URLs** via API keys, not live server filesystems.

---

## Optional environment variables

```bash
export RENDER_API_KEY=...
export NETLIFY_AUTH_TOKEN=...
```

---

*Keep this file aligned with code: when you add routes or models, update the tables above.*
