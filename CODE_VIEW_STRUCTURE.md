# Code View - Project Structure Setup

## Core Architecture with Live Feed

### Backend Structure
```
backend/
├── main.py                 # FastAPI app with WebSocket support
├── requirements.txt        # Dependencies including tree-sitter
├── analysis/
│   ├── __init__.py
│   ├── ingestion.py        # GitHub/local repo intake
│   ├── evidence.py         # Core evidence model
│   ├── scheduler.py        # Live monitoring scheduler
│   ├── live_feed.py        # Real-time change detection
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py         # Abstract parser interface
│   │   ├── python_parser.py # Python AST + tree-sitter
│   │   └── javascript_parser.py # JS/TS parsing
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── claims_extractor.py # README/docs analysis
│   │   ├── route_extractor.py  # API endpoint discovery
│   │   └── symbol_extractor.py # Functions/classes
│   ├── tracers/
│   │   ├── __init__.py
│   │   ├── flow_tracer.py      # Data flow analysis
│   │   └── dependency_tracer.py # Dependency mapping
│   └── detectors/
│       ├── __init__.py
│       ├── contradiction_detector.py # Claims vs reality
│       └── boundary_detector.py     # Trust boundaries
├── models/
│   ├── __init__.py
│   ├── evidence.py         # Evidence data models
│   ├── analysis.py         # Analysis session models
│   └── monitoring.py       # Live feed models
├── api/
│   ├── __init__.py
│   ├── routes.py           # Analysis endpoints
│   ├── monitoring.py       # Live feed endpoints
│   └── websocket.py        # Real-time updates
└── database.py            # SQLite setup
```

### Frontend Structure with Live Updates
```
frontend/
├── package.json
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── LiveFeed.tsx        # Real-time updates
│   │   ├── EvidenceCard.tsx    # Evidence display
│   │   └── AnalysisProgress.tsx # Progress tracking
│   ├── views/
│   │   ├── Triage.tsx          # Dashboard
│   │   ├── Claims.tsx          # Claims analysis
│   │   ├── Mechanisms.tsx      # Implementation
│   │   ├── Boundaries.tsx      # Trust boundaries
│   │   ├── Contradictions.tsx  # Gaps detected
│   │   ├── LiveMonitor.tsx     # Continuous monitoring
│   │   └── Evidence.tsx        # Evidence browser
│   ├── hooks/
│   │   ├── useWebSocket.tsx    # Real-time connection
│   │   ├── useAnalysis.tsx     # Analysis state
│   │   └── useEvidence.tsx     # Evidence queries
│   └── utils/
│       ├── api.ts              # API client
│       └── evidence.ts         # Evidence utilities
```

### Live Feed Capabilities

1. **Real-time Repository Monitoring**
   - Git webhook integration
   - Scheduled polling for changes
   - Diff analysis on new commits
   - Evidence evolution tracking

2. **Change Detection Pipeline**
   - Code structure changes
   - Documentation updates
   - Dependency modifications
   - Security boundary violations

3. **Evidence Timeline**
   - Historical analysis snapshots
   - Confidence degradation tracking
   - Contradiction emergence alerts
   - Trust path evolution

4. **WebSocket Live Updates**
   - Real-time analysis progress
   - New finding notifications
   - Contradiction alerts
   - Health status changes

## Implementation Priority

Phase 1 MVP includes:
- [x] Project structure
- [ ] Core evidence model
- [ ] Python/JS parsers with tree-sitter
- [ ] Basic analysis pipeline
- [ ] Claims extraction from docs
- [ ] Simple contradiction detection
- [ ] React frontend with WebSocket
- [ ] Live monitoring foundation
- [ ] GitHub webhook integration

Want to start with the backend evidence model or the live monitoring architecture?
