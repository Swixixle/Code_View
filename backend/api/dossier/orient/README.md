# Orient Dossier

Composition layer on top of Code View's evidence pipeline and archaeology. Presents the same evidence through different audience-specific vantages (operator, reviewer, contributor, auditor) without issuing advice, opinions, or recommendations.

**Before extending this module — including adding a new view, relaxing a test, or widening a query filter — read the design & discipline doc:**

> [`/docs/orient_dossier.md`](../../../../docs/orient_dossier.md)

That doc is the contract. This directory is its implementation.

## Quick orientation

- `router.py` — FastAPI routes, mounted at `/api/dossier/orient`.
- `views/` — one file per audience view. Each view composes `Slot`s from `queries.py` only.
- `queries.py` — the single seam to existing evidence/archaeology APIs. The only place this module touches Code View internals.
- `composition.py` — renders a view's slot dict to markdown.
- `templates/` — Jinja2 templates. Dumb: they iterate and branch filled-vs-gap. No logic.

## Non-negotiable

The forbidden-content tripwire for rendered orient markdown (denylist of advisory phrases — see **Tests** in [`docs/orient_dossier.md`](../../../../docs/orient_dossier.md)) is CI, not a style preference. If it fails, fix the copy or consciously relax the test with a changelog entry in that doc. Do not bypass it.
