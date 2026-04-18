# Code View

**Evidence-backed code dissection engine that shows how software systems actually work.**

Code View is a forensic analysis tool that strips any codebase down to its fundamental components: claims, mechanisms, boundaries, and contradictions. Unlike traditional code analyzers that guess or summarize, Code View provides evidence trails for every finding.

## What Makes Code View Different

🔍 **Evidence-First Analysis** - Every finding shows exactly where it came from with full provenance trails

🎯 **Contradiction Detection** - Identifies where documentation, UI, or claims differ from actual implementation

🛡️ **Boundary Analysis** - Shows where systems stop being justified (unsigned fields, mocks, placeholders)

📊 **Multi-Pass Transparency** - Displays analysis stages, confidence levels, and what remains unknown

⚡ **Claims vs Mechanisms** - Systematic mapping of what systems claim to do versus how they actually work

## Core Views

- **Triage Dashboard** - System type, critical paths, contradictions, coverage confidence
- **Claims** - What the codebase says it does (extracted from docs, comments, UI)
- **Mechanisms** - How claims are actually implemented in code
- **Boundaries** - Where justification stops and assumptions begin
- **Contradictions** - Where reality differs from presentation
- **Architecture** - Flow diagrams with trust paths and dependency mapping
- **Evidence** - Universal drill-down with full provenance for every finding

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Code_View.git
cd Code_View

# Backend setup
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and enter a GitHub URL to begin analysis.

### Example Analysis

```bash
# Analyze a repository
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"source": "https://github.com/example/repo", "mode": "deep"}'

# Get evidence for a specific finding
curl http://localhost:8000/evidence/claim-001
```

## Architecture

### Analysis Pipeline

1. **Ingestion** - Source extraction and classification
2. **Symbol Extraction** - Functions, routes, models, configurations
3. **Flow Tracing** - Data paths and call graphs
4. **Claim Extraction** - Capability statements from docs/UI
5. **Contradiction Detection** - Implementation vs presentation gaps
6. **Evidence Assembly** - Provenance trails for all findings

### Evidence Model

Every finding includes:
- **Claim** - What was found or analyzed
- **Status** - supported/contradicted/unknown/not_verified
- **Evidence Type** - extracted/observed/inferred/heuristic
- **Source Locations** - Exact files and line numbers
- **Confidence Level** - high/medium/low
- **Boundary Notes** - Limitations and assumptions

## Language Support

- **Python** - FastAPI, Django, Flask, SQLAlchemy
- **JavaScript/TypeScript** - Express, React, Next.js
- **Go** - Standard library, popular frameworks
- **Rust** - Cargo projects, web frameworks
- **Java** - Spring, Maven projects

## Use Cases

### Code Review
- Understand unfamiliar codebases quickly
- Identify security boundaries and trust assumptions
- Find contradictions between docs and implementation

### Due Diligence
- Technical assessment of acquired codebases
- Verification of claimed capabilities
- Security posture evaluation

### Architecture Analysis
- System boundary identification
- Data flow mapping
- Dependency risk assessment

### Security Analysis
- Attack surface mapping
- Trust boundary verification
- Input validation coverage

## Development

### Backend Structure
```
backend/
├── main.py              # FastAPI application
├── analysis/
│   ├── parsers/         # Language-specific parsers
│   ├── extractors/      # Symbol and route extraction
│   ├── tracers/        # Flow analysis
│   └── detectors/      # Contradiction detection
└── models/             # Data models and schemas
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/     # Reusable React components
│   ├── views/         # Main analysis views
│   ├── hooks/         # Custom hooks
│   └── utils/         # Helper functions
└── public/            # Static assets
```

### Adding New Parsers

1. Create parser in `backend/analysis/parsers/`
2. Implement the `BaseParser` interface
3. Register in `backend/analysis/registry.py`
4. Add tests in `tests/parsers/`

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Integration tests
npm run test:e2e
```

## Configuration

### Analysis Modes

- **Quick** - Basic symbol extraction (< 30 seconds)
- **Standard** - Full analysis with flow tracing (1-2 minutes)
- **Deep** - Complete analysis with runtime inference (5+ minutes)

### Environment Variables

```bash
# Backend
DATABASE_URL=sqlite:///code_view.db
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards

- **Backend**: Black formatting, type hints, 90%+ test coverage
- **Frontend**: Prettier formatting, TypeScript strict mode, component tests
- **Documentation**: Every public function documented
- **Evidence**: All analysis outputs must include provenance

## License

MIT License - see [LICENSE](LICENSE) for details.

## Roadmap

### v1.0 (MVP)
- [x] Core analysis engine
- [x] Python/JavaScript support
- [x] Evidence data model
- [x] Basic web interface

### v1.1 (Enhanced Analysis)
- [ ] Contradiction detection
- [ ] Claims vs mechanisms mapping
- [ ] Enhanced visualizations
- [ ] Go/Rust language support

### v1.2 (Production Features)
- [ ] Team collaboration
- [ ] Report generation
- [ ] API rate limiting
- [ ] Plugin system

### v2.0 (Advanced Features)
- [ ] Runtime analysis
- [ ] Security scanning
- [ ] CI/CD integration
- [ ] Enterprise features

## Support

- **Documentation**: [docs.codeview.dev](https://docs.codeview.dev)
- **Issues**: [GitHub Issues](https://github.com/yourusername/Code_View/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Code_View/discussions)
- **Security**: security@codeview.dev

## Acknowledgments

Built for developers who need to understand how software systems actually work, not just how they're presented. Inspired by the need for evidence-based code analysis in an era of increasing software complexity.

---

**"Show me the evidence, not the story."**
