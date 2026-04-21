# Orient Dossier — Design & Discipline

**Status:** Operator view implemented. Reviewer, contributor, and auditor views pending.

Code entry when working in the module: [`backend/api/dossier/orient/README.md`](../backend/api/dossier/orient/README.md).

The orient dossier is a composition layer on top of Code View's existing evidence pipeline and archaeology. It presents the same evidence through different audience-specific vantages without issuing advice, opinions, or recommendations. This document is the discipline contract for anyone extending it.

If you are adding a new view, start here. If you are relaxing a test, start here. If you are wondering why a slot renders an explicit gap instead of being hidden, start here.

---

## The discipline

Every sentence in every orient dossier must be traceable to one of three things:

1. An `evidence_id` (from the evidence pipeline)
2. An `entity_id` (from archaeology)
3. A **stated gap** — e.g. "No entry point detected" — which is itself a fact about the analysis, not a guess.

The dossier never issues advice, opinions, or suggestions about what the code "should" do or "could be good with." It does not generate prose that is not grounded in a query result. If a template slot has no evidence to fill it, it renders as an explicit gap ("No signing-related evidence found in indexed evidence") rather than being omitted or softened.

This is the same receipts-not-verdicts rule the rest of the project runs on. The orient dossier is a composition layer over existing evidence. It does no new inference.

---

## Why audience-specific views

The same repo surfaces different facts depending on who is looking. Rather than producing one generic "overview" that tries to serve everyone (and therefore serves no one), orient emits the same underlying evidence through distinct compositional templates:

- **Operator view** — someone trying to boot the system.
- **Reviewer view** (pending) — someone checking whether the code matches the claims it makes about itself.
- **Contributor view** (pending) — someone trying to make a safe change.
- **Auditor view** (pending) — someone checking what is signed, what is verifiable, and what is asserted but unsupported.

Each view is a deterministic composition of query results over existing evidence/archaeology APIs. No view generates content from an LLM, from inference, or from the view code itself. If you find yourself wanting a model to "smooth the prose," the prose is intentionally minimal and you are about to break the contract.

---

## Operator view

**Audience:** someone who just cloned the repo and needs to boot it. They are not trying to understand the domain, audit claims, or contribute — they need to get a process running and know whether it is running correctly.

**Falsifiable test:** a human who has never seen the codebase should be able to read the operator dossier and either (a) get the system running, or (b) know exactly which piece is missing. No guessing, no "figure it out."

The operator view answers, in order:

1. **What is this process?** — One sentence derived from the repo's top-level README title/tagline if present, plus the detected entry points. If neither is present, render "Process identity could not be determined from available evidence" and stop there for this section.
2. **What does it need installed?** — Runtime + package manager + declared dependencies. Pulled from `requirements.txt`, `package.json`, `pyproject.toml`, `Dockerfile`, detected language versions. Never inferred beyond what is declared.
3. **What are the entry points?** — Enumerated from archaeology: ASGI/WSGI app objects, `if __name__ == "__main__"` blocks, CLI `Typer`/`argparse` mains, `npm` scripts declared in `package.json`. Each with file path and line number.
4. **What is the boot sequence?** — Static import order from the entry points outward, bounded to depth 2 by default. The "assembly order" — what must exist before what can start. Derived from static imports plus known framework patterns (FastAPI app creation, middleware registration, route inclusion, DB engine creation). If the sequence cannot be determined statically, say so per-entry-point.
5. **What external services does it reach?** — From the evidence pipeline's existing detection: HTTP client calls, DB connection strings, env var reads, websocket endpoints. Each with file+line.
6. **What would a successful boot look like?** — Derived from declared ports (CORS config, uvicorn args, vite config), declared health endpoints (`/health`, `/healthz`, `/ping` route registrations detected in archaeology), declared startup log lines if grep-detectable.
7. **Known warnings.** — The contradictions the evidence pipeline already surfaces, filtered to ones that affect boot (missing declared files, broken imports, config referenced but not present). **Not** all contradictions — only boot-affecting.

Each section is a template slot. Each slot is filled by a specific query against existing evidence/archaeology APIs. If the query returns empty, the slot renders as a stated gap. The composition code does not fabricate filler.

---

## Module layout

```
backend/api/dossier/orient/
├── __init__.py
├── README.md              # pointer to this doc
├── router.py              # FastAPI router, mounts /api/dossier/orient
├── views/
│   ├── __init__.py
│   ├── base.py            # OrientView abstract base + shared query helpers
│   └── operator.py        # OperatorView
├── composition.py         # renders a View's slot dict to markdown via a template
├── templates/
│   └── operator.md.j2     # Jinja2 template for operator view
└── queries.py             # thin wrappers around existing evidence/archaeology calls
backend/tests/dossier/
├── __init__.py
└── test_operator_view.py
```

The orient dossier is a new sibling to the existing forensic and comparative dossiers under `backend/api/dossier/`. It does not modify them.

---

## API surface

```
GET /api/dossier/orient/{analysis_id}?view=operator
```

- `analysis_id` is the same ID returned by `POST /api/analysis/analyze`.
- `view` is a query param, defaults to `operator`. Any value for a view not yet implemented returns `501 Not Implemented` with body `{"detail": "View '<n>' not yet implemented. Available: operator."}`. Unimplemented views are not stubbed as empty templates — a 501 is honest, an empty template is a lie.
- Response: `text/markdown; charset=utf-8`, `Content-Disposition: attachment; filename="orient_<view>_<analysis_id>.md"`.
- On missing `analysis_id`: `404` with clear body.
- On analysis that has no archaeology run (i.e. `run_archaeology=false` was used): `409 Conflict` with body explaining that operator view requires archaeology and pointing to re-analyze with `run_archaeology=true`. Silent degradation is worse than a hard failure for this kind of tool.

---

## Composition rules

`backend/api/dossier/orient/views/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class Slot:
    """A single template slot. Either filled with evidence or an explicit gap."""
    name: str
    filled: bool
    content: Any              # structured payload the template renders
    gap_reason: str | None    # required if filled=False, explains why nothing
    sources: list[str]        # evidence_ids + entity_ids backing this slot

class OrientView(ABC):
    name: str

    @abstractmethod
    async def build_slots(self, analysis_id: str) -> dict[str, Slot]:
        ...
```

Each view implements `build_slots` with one method per slot:

```python
class OperatorView(OrientView):
    name = "operator"

    async def build_slots(self, analysis_id: str) -> dict[str, Slot]:
        return {
            "identity":         await self._identity(analysis_id),
            "requirements":     await self._requirements(analysis_id),
            "entry_points":     await self._entry_points(analysis_id),
            "boot_sequence":    await self._boot_sequence(analysis_id),
            "external_reach":   await self._external_reach(analysis_id),
            "success_signals":  await self._success_signals(analysis_id),
            "boot_warnings":    await self._boot_warnings(analysis_id),
        }
```

**Rule for every `_slot` method:** it may only call into `queries.py`. It may not touch the AST, filesystem, or git directly. If `queries.py` returns empty, the slot returns `Slot(filled=False, ...)` with a specific `gap_reason`. No method synthesizes content from the view code itself.

`queries.py` is the only place that reaches into existing evidence/archaeology APIs. This is the single testable seam.

**On evolving the base class:** if a future view genuinely needs different primitives (claim extraction for reviewer, temporal diff, contradiction ranking), that is a signal to evolve the abstraction — not to contort the new view into the operator-shaped mold. Do not freeze `OrientView` into shapes that block divergence.

---

## Template rules

The template is dumb. It renders slots, it does not contain logic beyond iteration and filled-vs-gap branching.

```markdown
# Orient: Operator View

**Analysis:** {{ analysis_id }}
**Repo:** {{ repo_identifier }}
**Commit:** {{ commit_sha }}
**Generated:** {{ generated_at }}

> This view is for getting the system running. It is not a review, audit, or
> endorsement. Every claim below traces to evidence in this repo at the commit
> above. Gaps are stated, not guessed.

---

## 1. What this process is

{% if slots.identity.filled %}
{{ slots.identity.content.statement }}

_Sources: {{ slots.identity.sources | join(", ") }}_
{% else %}
_Gap: {{ slots.identity.gap_reason }}_
{% endif %}

## 2. What it needs installed

{% if slots.requirements.filled %}
{% for req in slots.requirements.content.requirements %}
- **{{ req.ecosystem }}** — {{ req.summary }} (declared in `{{ req.source_file }}`)
{% endfor %}
{% else %}
_Gap: {{ slots.requirements.gap_reason }}_
{% endif %}

## 3. Entry points
...
```

Continue the same filled/gap pattern for every slot. No slot is omitted. No slot is silently empty.

---

## Queries

Each query in `queries.py` is a thin async function that calls existing Code View internals and returns a typed result. None of these add new analysis — every query below maps to a capability the codebase already has.

1. `get_repo_metadata(analysis_id)` — repo URL/path, commit_sha, top-level README path if present.
2. `get_readme_headline(analysis_id)` — first H1 + first paragraph of root README, or None.
3. `get_declared_requirements(analysis_id)` — list of `(ecosystem, source_file, parsed_contents)` for `requirements.txt`, `package.json`, `pyproject.toml`, `Dockerfile`. Parse minimally; do not resolve transitively.
4. `get_entry_point_entities(analysis_id)` — archaeology query for entities matching known entry-point patterns:
   - Python: `if __name__ == "__main__"` blocks, FastAPI/Flask `app = ...` assignments at module level, `Typer()` / `argparse.ArgumentParser()` mains.
   - JS: `package.json` `scripts` entries, any detected `main` field.
5. `get_static_import_tree(entity_id, depth=2)` — existing `trace` API with a depth bound.
6. `get_external_reach_evidence(analysis_id)` — existing evidence search filtered to categories: HTTP clients, DB connections, env var reads, websocket endpoints. This capability exists in the evidence pipeline — use it, do not re-implement.
7. `get_declared_ports_and_health(analysis_id)` — search evidence + archaeology for uvicorn/gunicorn port args, CORS origins, vite `server.port`, route registrations matching `/health`, `/healthz`, `/ping`, `/status`.
8. `get_boot_affecting_contradictions(analysis_id)` — existing contradiction set, filtered by a small allow-list of categories: `missing_file`, `broken_import`, `missing_config_reference`. **Do not widen this filter without explicit discussion.** The operator view must not become a dumping ground for every contradiction the pipeline finds.

If any capability above is missing from the current codebase, the orient PR stops and flags it. Any pipeline extension gets its own review so it does not hide under "orient work."

---

## Tests

`test_operator_view.py` covers, at minimum:

1. **Happy path fixture** — a synthetic analysis with all slots fillable. Every section renders with content, no "Gap:" strings appear.
2. **All-gaps fixture** — analysis where every query returns empty. Every section renders as a gap with a specific `gap_reason` (not a generic "no data"). No section is silently omitted.
3. **Mixed fixture** — some slots filled, some gaps. Both render correctly in the same document.
4. **No-archaeology fixture** — analysis persisted with `run_archaeology=False`. The endpoint returns `409`, not a partial dossier.
5. **Source traceability invariant** — for every filled slot in the happy-path fixture, `slot.sources` is non-empty and every ID in it resolves against the fixture's evidence/entity stores. This is the machine-checkable version of the discipline rule at the top of this doc.
6. **Forbidden-content invariant (tripwire)** — the rendered markdown is scanned against a denylist of advisory phrases: `"you should"`, `"consider"`, `"recommend"`, `"good for"`, `"could be"`, `"might want to"`. None may appear.

**Status of the tripwire test:** non-negotiable CI. If it fails, we fix the copy *or* consciously relax the test — never bypass it. Relaxing the test requires an entry in the changelog at the bottom of this doc explaining why.

Fixtures go under `backend/tests/dossier/fixtures/` as JSON. Do not depend on a real git clone.

---

## What this module does not do

- **No LLM in the orient pipeline.** Every slot is a deterministic query over structured evidence.
- **No frontend page.** The dossier is markdown-only until all four views exist and composition rules have stabilized.
- **No widening of the boot-affecting-contradictions filter.** Operator view is about getting running, not about surfacing every concern.
- **No collapsing gaps into polite absence.** A missing slot is information. Render it.
- **No advice.** Not in the template, not in the slot content, not in future views. The tripwire test enforces this mechanically.

---

## Adding a new view

1. Read this doc end-to-end.
2. Do not copy `operator.py` and edit it. Start from `base.py` and ask what the new audience actually needs.
3. If new primitives are needed in `queries.py`, add them there — not in the view.
4. If the new view needs genuinely new analysis from the evidence pipeline or archaeology, that is a separate PR that lands first. Orient PRs are composition only.
5. Add a tripwire-equivalent test for the new view's rendered output.
6. Add a changelog entry below.

---

## Success criterion

Someone clones an unfamiliar Code View-analyzed repo, runs the orient endpoint, reads the markdown, and either boots the system or knows precisely which piece is missing — without the dossier ever telling them what to think about the code.

If the dossier reads like advice, the module has failed. If it reads like an IKEA manual that knows when a part is missing, it has succeeded.

---

## Changelog

- **2026-04-21** — Initial spec. Operator view only. Reviewer, contributor, and auditor views pending. Tripwire denylist established as non-negotiable CI.
