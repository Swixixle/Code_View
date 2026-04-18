# Code View — notes from a self-analysis run

**Date:** 2026-04-18  
**Repository:** https://github.com/Swixixle/Code_View  
**Commit referenced in original note:** `b951bcf` (main)  
**Original run duration (reported):** ~1.3s  

This file replaces the informal `code_view_final_self_analysis.md` draft. It records **what one analysis run reported** and **how to read it**, without treating the engine as an external validator of “truth” or “institutional credibility.”

---

## What the pipeline produced (representative run)

Figures below come from the original self-analysis export; **re-run** `POST /api/analysis/analyze` on the repo to reproduce or compare.

| Metric | Value (original run) |
|--------|----------------------|
| Evidence items | 120 |
| Claims assembled | 76 |
| Mechanisms | 3 |
| Stages / categories touched | Multiple (e.g. python parsing, enhanced claims, doc-style claims) |

**Evidence mix (reported):** almost all items labeled as direct extraction from code/docs; a small fraction inferred heuristically.

---

## How to interpret this

1. **Counts are not a quality score.** They reflect how many structured items the heuristics emitted for this tree, not “correctness” or fitness for any particular institution.
2. **“Claims” are often doc-derived.** Phrases about “institutional review,” “dossiers,” or “live monitoring” are matched against README and similar text; they describe **stated** product goals, not independent certification.
3. **Crypto-related items** are pattern- and language-based (e.g. SHA-256 mentioned in tests or docs). They are **not** a cryptographic audit.
4. **Self-analysis is a smoke test**, useful to see that parsing, persistence, and reporting run end-to-end—not a proof that the system “validates its thesis.”

---

## Example categories (from the original report)

The run attributed findings to stages such as:

- Python AST / parsing-related evidence  
- Enhanced / documentation-style claims extraction  
- Credibility- or security-language heuristics  
- Feature and mechanism-style buckets  

Exact labels depend on the `analysis_stage` and refinement configuration in that commit.

---

## Relation to the README

If README wording changes, **claims extracted from documentation will change** even when implementation is unchanged. Treat cross-version comparisons as **documentation drift**, not regression by default.

---

## Reproduce

```bash
cd backend
.venv/bin/uvicorn main:app --port 8000
```

```bash
curl -s -X POST http://localhost:8000/api/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"source": "/absolute/path/to/Code_View", "persist": true, "run_archaeology": true}'
```

Use returned `analysis_id` with `GET /api/analysis/{analysis_id}` or persisted store APIs. For archaeology, use `repo_id` and `commit_sha` from the response.

---

*This document is descriptive metadata about a self-run, not an endorsement or third-party assessment.*
