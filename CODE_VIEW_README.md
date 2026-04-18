# Code View

**Evidence-backed code dissection and Python-first static archaeology**

Code View examines software with source-level evidence: Python AST parsing, documentation claims, heuristic crypto/security language, and an optional **entity index** (functions, classes, routes, imports, static call edges). It is useful for review and exploration; outputs are **signals for human verification**, not automated verdicts on trustworthiness.

**Developers / Cursor:** see **[CURSOR.md](./CURSOR.md)** for import layout, entry points, API tables, and extension notes.

---

## What Code View Does

- **Extracts evidence** from Python source (AST) with file/line provenance
- **Surfaces documentation claims** and compares them heuristically to observed code (contradictions are **pattern-based**, not formal proofs)
- **Refines evidence** (deduplication, pattern labels, optional tone/review metadata) for defensible summaries
- **Indexes entities** (module/class/function/method/route when derivable) with **resolve / identify / trace / interpret / project** APIs
- **Ingests code** from git, local paths, zip upload or URL, and (optionally) Render/Netlify-linked git URLs via their APIs
- **Persists** analyses and archaeology to **SQLite** (`data/code_view.db` under the repo root)
- **Educational dossiers** as Markdown downloads
- **Monitoring hooks** (polling GitHub for new commits when configured) with WebSocket notifications; not a full live IDE integration

---

## Quick Start

### Prerequisites

- **Python** 3.11+ (recent versions tested; use a venv)
- **Node.js** 18+ (for the bundled frontend)
- **Git** (for cloning remotes and archaeology metadata)

### Backend

```bash
git clone https://github.com/Swixixle/Code_View.git
cd Code_View/backend

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API base: `http://localhost:8000` — OpenAPI docs at `/docs`.

### Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Dev server defaults to **port 3000** with `/api` and `/ws` proxied to the backend (`frontend/vite.config.js`). Open **http://localhost:3000**.

---

## Architecture (concise)

```
Backend (FastAPI)
├── Evidence pipeline     # Python AST + doc claims + refinement + mechanisms/contradictions
├── Archaeology           # Entity extraction, SQLite graph, resolve/identify/trace/interpret/project
├── Universal ingestion     # clone, local dir, zip upload/URL, optional Render/Netlify → git URL
├── Persistence             # SQLite (SQLAlchemy async)
├── Dossiers                # Markdown generation from stored or fresh analysis
├── Monitoring / WebSocket  # optional GitHub HEAD polling + /ws/live-feed
└── REST + WS               # /api/analysis/*, /api/dossier/*, /api/monitoring/*, …

Frontend (React + Vite, under frontend/src/)
└── Dashboard UI (scaffold; wire to API as needed)
```

`main.py` enables CORS for `http://localhost:3000` by default.

---

## Universal ingestion

Check which platform APIs are available (no secrets returned):

```bash
curl "http://localhost:8000/api/analysis/ingest/capabilities"
```

| Endpoint | Body / form | Notes |
|----------|-------------|--------|
| `POST /api/analysis/ingest/archive` | multipart: `file`, optional `persist`, `run_archaeology`, etc. | `.zip` extracted with path traversal checks |
| `POST /api/analysis/ingest/zip-url` | JSON: `url`, plus `persist`, `run_archaeology`, … | HTTPS zip download |
| `POST /api/analysis/ingest/git` | JSON: `repo_url`, … | Shallow clone |
| `POST /api/analysis/ingest/local` | JSON: `directory_path`, … | Must be a directory on disk |
| `POST /api/analysis/ingest/render` | JSON: `service_id`, … | Requires `RENDER_API_KEY`; uses Render API to find linked **git** URL, then clones |
| `POST /api/analysis/ingest/netlify` | JSON: `site_id`, … | Requires `NETLIFY_AUTH_TOKEN`; uses Netlify API for linked **repo_url**, then clones |
| `POST /api/analysis/ingest/replit` | JSON: `git_url` and/or `zip_url`, … | No Replit session API; you supply export zip or git remote |

Legacy single entrypoint (still supported):

```bash
curl -X POST http://localhost:8000/api/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"source": "https://github.com/org/repo", "persist": true, "run_archaeology": true}'
```

Analyze responses include **`repo_id`** and **`archaeology`** counts when indexing succeeded.

---

## Archaeology (entity-level)

After a successful indexed run, use **`repo_id`** and **`commit_sha`** from the analysis response (or entity records).

**Resolve** line → entity (JSON uses **`commit_sha`**, not `commit_hash`):

```bash
curl -X POST http://localhost:8000/api/analysis/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "<repo_id from analyze>",
    "commit_sha": "<40-char commit>",
    "file_path": "backend/main.py",
    "line": 46
  }'
```

**Taps** (replace `ENTITY_ID`):

```bash
curl "http://localhost:8000/api/analysis/entity/ENTITY_ID/identify"
curl "http://localhost:8000/api/analysis/entity/ENTITY_ID/trace"
curl "http://localhost:8000/api/analysis/entity/ENTITY_ID/interpret?repo_path=/abs/path/to/repo"
curl "http://localhost:8000/api/analysis/entity/ENTITY_ID/project"
```

- **interpret** uses git history when **`repo_path`** points at a local checkout; otherwise it reports explicit gaps.
- **project** uses **static** reverse edges only; confidence is conservative.

---

## Evidence search and dossiers

```bash
curl "http://localhost:8000/api/analysis/evidence/search?query=ed25519&limit=10"
```

**Dossier** (Markdown download):

```bash
curl -X POST http://localhost:8000/api/dossier/analyze-with-dossier \
  -H "Content-Type: application/json" \
  -d '{"source": "https://github.com/your/repository", "persist": true}' \
  -o forensic_dossier.md
```

**Comparative** (2–5 HTTPS git URLs only):

```bash
curl -X POST http://localhost:8000/api/dossier/comparative-dossier \
  -H "Content-Type: application/json" \
  -d '{"repositories": ["https://github.com/a/one", "https://github.com/b/two"]}' \
  -o comparative.md
```

**Stored** analysis dossier:

```bash
curl "http://localhost:8000/api/dossier/report/ANALYSIS_ID" -o stored.md
```

---

## Cryptography and security language

The pipeline looks for **common patterns and wording** in code and docs (e.g. signing, hashing, Ed25519, SHA-256). It does **not** perform deep cryptographic audits or protocol verification. Treat findings as **leads**, not certifications. Any mention of specific schemes (e.g. JCS) in reports usually comes from **observed text in the repository**, not a dedicated JCS verifier in Code View.

---

## Evidence refinement (existing analyses)

- Deduplication and labeling to reduce inflated counts
- Optional **`refinement`** metadata on summaries where the refinement stage ran
- See **`GET /api/analysis/{id}/summary`**

---

## Configuration

**Database:** SQLite at **`Code_View/data/code_view.db`** (created on startup). The code uses a fixed `DATABASE_URL` in `backend/database.py`; changing DB location means editing that module or extending config (there is no separate `.env`-driven DB URL in-tree today).

**Platform APIs (optional):**

```env
RENDER_API_KEY=...
NETLIFY_AUTH_TOKEN=...
```

**CORS:** Defaults include `http://localhost:3000` in `main.py`.

---

## API reference (high level)

**Ingestion:** `GET /api/analysis/ingest/capabilities`, `POST …/ingest/{archive,zip-url,git,local,render,netlify,replit}`  

**Analysis:** `POST /api/analysis/analyze`, `GET /api/analysis/analyses`, `GET /api/analysis/{analysis_id}`, `GET /api/analysis/{analysis_id}/summary`, `GET /api/analysis/evidence/search`, `GET /api/analysis/evidence/{evidence_id}`  

**Archaeology:** `POST /api/analysis/resolve`, `GET /api/analysis/entity/{entity_id}/{identify,trace,interpret,project}`  

**Dossier:** `POST /api/dossier/analyze-with-dossier`, `POST /api/dossier/comparative-dossier`, `GET /api/dossier/report/{analysis_id}`  

**Monitoring:** `POST|GET /api/analysis/monitoring/repository`  

**WebSocket:** `WS /ws/live-feed`  

**Health:** `GET /health`, `GET /`

Full detail: **`/docs`** (Swagger).

---

## Project layout (verified)

```
Code_View/
├── backend/
│   ├── analysis/          # engine, parsers, refinement, archaeology/, ingestion/
│   ├── api/               # routes, dossier, monitoring, websocket
│   ├── models/, persistence/
│   ├── main.py
│   └── tests/             # e.g. test_archaeology.py
├── frontend/
│   ├── src/               # App.jsx, CodeViewDashboard.jsx, …
│   └── vite.config.js
├── data/                  # SQLite DB (gitignored if listed)
├── CODE_VIEW_SPEC.md, CODE_VIEW_STRUCTURE.md, CODE_VIEW_README.md
└── _zip12/                # optional reference snippets (not the main app)
```

---

## Limitations

- **Heuristic and static:** crypto claims, contradictions, call graph, and impact projection are **not** runtime-complete.
- **Python-first** for deep AST and entity extraction; other languages may appear in file counts but are not fully modeled.
- **Hosting APIs** (Render/Netlify) resolve **git** links, not arbitrary “live server filesystems.”
- **No claim of institutional scoring** as an objective metric—reports are for review.

---

## License

MIT is the **intended** license for this project; confirm a **`LICENSE`** file exists in your checkout and keep it in sync with maintainers.

---

**Code View:** evidence-first exploration and static archaeology—verify important conclusions in code and process.
