# Code View - Evidence-Backed Code Dissection Engine

## Product Vision

**A code dissection engine that strips any software system into claims, mechanisms, flows, dependencies, boundaries, and contradictions — with evidence for every finding.**

Not a repo browser. Not a code analyzer that guesses. A forensic tool that shows exactly what was found, what was inferred, what was tested, what was contradicted, and what remains unknown.

## Core Architecture

### Analysis Pipeline (Multi-Pass)
1. **Ingestion** - Clone/extract source
2. **File Classification** - Language detection, file type mapping  
3. **Symbol Extraction** - Functions, classes, routes, models
4. **Dependency Scanning** - Runtime, dev, external APIs, secrets
5. **Flow Tracing** - Data paths, call graphs, request flows
6. **Claim Extraction** - What the system says it does (README, docs, UI, comments)
7. **Mechanism Mapping** - How claims are actually implemented
8. **Boundary Detection** - Where justification stops (unsigned fields, mocks, placeholders)
9. **Contradiction Analysis** - Where docs/UI overstate reality
10. **Evidence Assembly** - Provenance for every finding

### Evidence System (Core Product)

Every finding must have:
```json
{
  "claim": "This system signs outputs with Ed25519",
  "status": "supported|contradicted|unknown|not_verified",
  "evidence_type": "extracted|observed|inferred|heuristic",
  "source_locations": ["signing.py:15-42", "routes.py:128"],
  "extracted_symbols": ["apply_signature", "verify_signature"],
  "reasoning_chain": ["found signing function", "found verify route", "canonicalization detected"],
  "counterevidence": ["key persistence assumptions unclear"],
  "confidence": "high|medium|low",
  "boundary_note": "some displayed fields may not be inside signing body"
}
```

## UI Architecture

### Main Views

#### 1. **Triage Dashboard** (replaces Overview)
- **System Type**: API / mobile app / monorepo / CLI / library / hybrid
- **Primary Surfaces**: routes, jobs, UI, DB, queues, signatures  
- **Critical Paths Found**: 3
- **Claims Extracted**: 18
- **Contradictions Detected**: 4
- **Unverified Areas**: 6
- **Coverage Confidence**: medium

#### 2. **Claims** (New - Core)
What the codebase says it does:
- Extracted from README, docs, UI text, route names, config, tests, comments
- Each claim linked to source location
- Status: verified/contradicted/unknown

#### 3. **Mechanisms** (New - Core)  
What actually implements those claims:
- Routes, services, adapters, call paths, signatures, queues, schemas, storage, renderers
- Traced from claim to implementation
- Shows gaps where claims have no mechanism

#### 4. **Boundaries** (New - Core)
Where the system stops being justified:
- Unsigned fields, mocked data, placeholders, weak coverage
- Fallback examples, missing infra, brittle assumptions
- Demo vs production separation issues

#### 5. **Architecture** (Enhanced)
Three modes:
- **Structural Graph**: Modules, routes, services, schemas, DB models
- **Runtime Flow**: Request → parser → service → adapter → persistence → output  
- **Trust Path**: Input → transformation → attestation → display

Every node shows: file origin, language, confidence, static vs runtime, direct vs inferred

#### 6. **Dependencies** (Enhanced)
- **Runtime Required** (cannot function without)
- **Build/Dev Only** 
- **External APIs** (fragile external dependencies)
- **Secrets/Keys Expected**
- **Infra Assumptions**  
- **Failure-Mode Sensitive Dependencies**

#### 7. **Contradictions** (New - Killer Feature)
- Docs claim X, code supports Y
- UI implies breadth, adapter support is narrow  
- Route exists, but auth posture is ambiguous
- Signature exists, but not all visible fields are attested
- Tests validate logic, but not deployment readiness
- Example/demo data mistaken for live behavior

#### 8. **Code Browser** (Enhanced)
Analytical overlays:
- Functions, Routes, External calls, DB writes
- Signature boundaries, Auth gates, Unvalidated input
- TODO/FIXME, Test references, Claimed feature references
- Toggle layers for focused analysis

#### 9. **Evidence** (Universal Drill-Down)
Every card in every view drills down to evidence
- Full provenance chain for every finding
- Source locations, extracted symbols, reasoning
- Confidence levels and boundary notes

### Analysis States (No Fake Data)
Every UI element shows its provenance:
- **Extracted** - Found in code/config
- **Observed** - Seen at runtime  
- **Inferred** - Logical deduction
- **Heuristic** - Pattern matching
- **Not Verified** - Present but unconfirmed
- **Unknown** - Insufficient information

## Technical Implementation

### Backend Stack
- **Python FastAPI** for analysis engine
- **Tree-sitter** for language parsing
- **NetworkX** for dependency graphs
- **SQLite** for evidence storage
- **Redis** for analysis caching
- **Semgrep** for pattern detection

### Frontend Stack  
- **React + TypeScript**
- **D3.js** for architecture visualization
- **Monaco Editor** for code viewing
- **TanStack Query** for state management
- **Tailwind CSS** for styling

### Source Intake System
```
Source Type: GitHub / zip / local folder / tarball
Primary Language: [auto-detected]
Analysis Mode: General / Trust / Security / Architecture / Diligence  
Runtime Allowed: yes/no
Internet Allowed: yes/no
Secrets Available: masked / none / injected
Depth: quick / standard / deep
```

### Analysis Engines

#### Language Parsers
- Python: AST + imports + decorators
- JavaScript/TypeScript: AST + modules + React components
- Go: AST + packages + interfaces
- Rust: AST + crates + traits
- Java: AST + packages + annotations

#### Extractors
- **Route Extractor**: FastAPI, Express, Spring, Django routes
- **Model Extractor**: SQLAlchemy, Mongoose, GORM models  
- **Config Extractor**: Environment variables, config files
- **Secret Scanner**: API keys, tokens, credentials
- **Dependency Mapper**: Package managers, imports, external calls

#### Analyzers
- **Flow Tracer**: Data flow through functions/services
- **Trust Boundary Detector**: Signed vs unsigned fields
- **Claim Extractor**: NLP on docs/comments for capability claims
- **Contradiction Detector**: Claims vs implementation gaps

## Repository Structure

```
Code_View/
├── README.md
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── analysis/
│   │   ├── ingestion.py        # Source intake
│   │   ├── parsers/            # Language-specific parsers
│   │   ├── extractors/         # Symbol/route/model extraction
│   │   ├── tracers/           # Data flow tracing
│   │   ├── detectors/         # Contradiction detection
│   │   └── evidence.py        # Evidence assembly
│   ├── models/                # Data models
│   └── api/                   # REST endpoints
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── views/            # Main view components
│   │   ├── hooks/            # Custom hooks
│   │   └── utils/            # Utilities
│   └── public/
└── tests/                     # Test suites
```

## Development Phases

### Phase 1: Core Engine (MVP)
- Source ingestion (GitHub + local)
- Python/JavaScript parsing
- Basic symbol extraction
- Evidence data model
- Simple web interface

### Phase 2: Analysis Depth
- Flow tracing
- Claim extraction from docs
- Contradiction detection
- Enhanced visualizations
- Multi-language support

### Phase 3: Production Features
- Runtime analysis
- Advanced security scanning
- Team collaboration
- Report generation
- Plugin system

## Success Metrics

**Technical Quality**
- Parse accuracy across languages (>95%)
- Evidence provenance completeness (100%)
- False positive rate (<5%)

**User Experience** 
- Time to first insight (<30 seconds)
- Analysis depth vs speed tradeoffs
- Contradiction detection accuracy

**Product Differentiation**
- Evidence trail completeness vs competitors
- "Unknown" result honesty
- Contradiction detection uniqueness

## Key Differentiators

1. **Evidence-First Architecture** - No finding without provenance
2. **Contradiction Detection** - Shows where reality differs from claims  
3. **Boundary Analysis** - Identifies where justification stops
4. **"Unknown" as Strength** - Honest about limitations
5. **Multi-Pass Transparency** - Shows analysis stages and confidence
6. **Claims vs Mechanisms** - Systematic gap analysis

This is not another code browser or repo summarizer. This is a forensic dissection tool that shows exactly how software systems actually work versus how they present themselves.

## Archaeology change log

- **2026-04-21** — Fixed static call graph resolution for cross-module calls: `from package.module import name` and relative `from .module` / `from ..module` imports now bind call edges to the defining entity. Re-exports through `package/__init__.py` are followed one step when the direct `package.symbol` qualified name is not an indexed entity. Regression: `backend/tests/archaeology/test_cross_module_trace.py`. Receipt: `docs/receipts/sweeps_relief_sign_bytes_grep.md`. *Follow-up (not this change): persist explicitly unresolved call targets (name + site) when the resolver cannot map a callee, so empty `trace` never means “resolver silently failed” — see `docs/orient_dossier.md` reviewer view.*
