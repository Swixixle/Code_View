# Code View

**Evidence-backed code dissection with cryptographic verification**

Code View is a forensic analysis platform that systematically examines software systems to reveal how they actually work versus how they present themselves. Built for civic accountability platforms, it provides evidence trails suitable for institutional review and adversarial scrutiny.

---

## 🎯 What Code View Does

Code View transforms software analysis from subjective assessment to **evidence-backed forensic examination**:

- **Extracts real evidence** from source code using Python AST parsing
- **Detects cryptographic infrastructure** (Ed25519, SHA-256, verification systems)
- **Maps claims vs implementation** to identify documentation gaps
- **Generates comprehensive dossiers** with institutional credibility assessment
- **Provides live monitoring** with real-time analysis updates

## 🏛️ Built for Institutional Credibility

Code View was designed to analyze civic accountability platforms where **"receipts, not verdicts"** matters:

- **Evidence trails** with exact source code references
- **Cryptographic verification** detection for trust boundaries
- **Educational documentation** explaining how systems actually work
- **Comparative analysis** across multiple platforms
- **Professional reporting** suitable for journalists and external review

## 🔬 Forensic Analysis Features

### Evidence Extraction
- **Python AST parsing** for functions, classes, routes, and imports
- **Cryptographic pattern detection** for signing, verification, and hashing
- **Documentation analysis** extracting capability claims
- **Trust boundary mapping** identifying verification checkpoints

### Evidence Refinement (defensible headline numbers)
- **Deduplication** of overlapping findings (exact, semantic, and repeated pattern spikes)
- **Pattern vs implementation labeling** (`refinement_signal` on each evidence item)
- **Tone calibration** and **human-review priorities** stored with the analysis
- Persisted on `GET /api/analysis/{id}/summary` as **`refinement`** when available

### Live Monitoring
- **Real-time repository monitoring** with change detection
- **WebSocket live feed** for analysis progress updates
- **Automatic re-analysis** on code changes
- **Regression detection** when evidence quality degrades

### Educational Dossiers
- **Comprehensive forensic reports** with methodology explanation
- **Architecture education** through pattern recognition
- **Trust assessment** with institutional credibility scoring
- **Comparative analysis** across multiple platforms

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/Swixixle/Code_View.git
cd Code_View/backend

# Create virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Start the backend
.venv/bin/uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Access the platform at http://localhost:3000**

## 📊 Platform Architecture

```
Code View Platform
├── Backend (FastAPI)
│   ├── Evidence Extraction      # Python AST + crypto detection
│   ├── Evidence Refinement      # Dedup, pattern vs implementation, review hints
│   ├── Persistence Layer      # SQLite with full relationships
│   ├── Live Monitoring        # WebSocket + repository watching
│   ├── Educational Dossiers   # Comprehensive report generation
│   └── REST API               # Analysis, evidence, monitoring endpoints
├── Frontend (React + Vite)
│   ├── Forensic Dashboard     # Dark theme evidence visualization
│   ├── Live Updates           # WebSocket integration
│   ├── Evidence Search        # Real-time filtering and exploration
│   └── Dossier Generation     # One-click report download
└── Analysis Pipeline
    ├── File Classification    # Language detection and categorization
    ├── Python Parsing         # AST extraction with source locations
    ├── Claims Extraction      # Documentation capability analysis
    ├── Evidence Refinement    # Dedup + labeling + tone/review metadata
    ├── Mechanism Mapping      # Implementation pattern detection
    ├── Contradiction Detection # Claims vs reality comparison
    └── Evidence Assembly      # Comprehensive finding compilation
```

## 🔍 Usage Examples

### Analyze a Repository
```bash
# REST API
curl -X POST http://localhost:8000/api/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"source": "https://github.com/your/repository", "persist": true}'

# Response includes evidence count, claims, contradictions, and mechanisms
```

### Search Evidence
```bash
# Find cryptographic implementations
curl "http://localhost:8000/api/analysis/evidence/search?query=ed25519&limit=10"

# Search for specific patterns
curl "http://localhost:8000/api/analysis/evidence/search?query=pattern&limit=10"
```

### Generate Educational Dossier
```bash
# Comprehensive forensic report
curl -X POST http://localhost:8000/api/dossier/analyze-with-dossier \
  -H "Content-Type: application/json" \
  -d '{"source": "https://github.com/your/repository"}' \
  -o forensic_dossier.md
```

### Compare Multiple Platforms
```bash
# Comparative analysis across repositories
curl -X POST http://localhost:8000/api/dossier/comparative-dossier \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      "https://github.com/platform/one",
      "https://github.com/platform/two"
    ]
  }' \
  -o comparative_analysis.md
```

## 🎓 Educational Value

Code View serves as both an analysis tool and educational platform:

### For Developers
- **Learn architecture patterns** from real civic technology systems
- **Understand cryptographic verification** through working examples
- **See evidence-first design** principles in practice

### For Institutions
- **Assess software credibility** with evidence-backed analysis
- **Verify claimed capabilities** against actual implementation
- **Understand trust boundaries** and verification mechanisms

### For Journalists
- **Investigate accountability platforms** with forensic rigor
- **Verify transparency claims** with evidence trails
- **Generate professional reports** for institutional review

## 🔐 Cryptographic Detection

Code View specifically detects:

- **Ed25519 digital signatures** for evidence verification
- **SHA-256 hashing** for data integrity
- **JCS canonicalization** for deterministic signing
- **Verification functions** for third-party validation
- **Trust boundaries** where assumptions begin
- **Receipt systems** for institutional accountability

## 🏗️ Development

### Project Structure
```
Code_View/
├── backend/
│   ├── analysis/                 # Evidence extraction and parsing
│   │   └── refinement/         # Dedup, classification, tone, human-review bundle
│   ├── api/                    # REST endpoints and WebSocket
│   ├── models/                 # Data models and ORM
│   ├── persistence/            # Database operations
│   └── main.py                 # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── CodeViewDashboard.jsx  # Main interface
│   │   └── App.jsx                # React app
│   ├── package.json            # Dependencies
│   └── vite.config.js          # Development configuration
└── CODE_VIEW_SPEC.md, CODE_VIEW_STRUCTURE.md   # Documentation at repo root
```

### Adding New Parsers
1. Create parser in `backend/analysis/parsers/`
2. Extend `AnalysisEngine` to use new parser
3. Add language detection to file classification
4. Update evidence models if needed

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request with clear description

## 📈 Performance

**Analysis Speed:**
- Small repositories (< 100 files): ~1-2 seconds
- Medium repositories (< 500 files): ~5-10 seconds  
- Large repositories (1000+ files): ~15-30 seconds

**Evidence Accuracy:**
- High confidence: 70-80% of findings (direct source extraction)
- Medium confidence: 15-20% of findings (pattern matching)
- Low confidence: 5-10% of findings (requires manual verification)

## 🔧 Configuration

### Backend Configuration
Environment variables in `backend/.env`:
```env
DATABASE_URL=sqlite:///data/code_view.db
WEBSOCKET_ORIGINS=http://localhost:3000
LOG_LEVEL=info
```

### Frontend Configuration  
Vite proxy in `frontend/vite.config.js`:
```javascript
server: {
  proxy: {
    '/api': 'http://127.0.0.1:8000',
    '/ws': { target: 'ws://127.0.0.1:8000', ws: true }
  }
}
```

## 📋 API Reference

### Analysis Endpoints
- `POST /api/analysis/analyze` - Analyze repository
- `GET /api/analysis/analyses` - List recent analyses
- `GET /api/analysis/{id}/summary` - Get analysis summary (includes optional **`refinement`** metadata)
- `GET /api/analysis/evidence/{id}` - Get specific evidence
- `GET /api/analysis/evidence/search` - Search evidence

### Dossier Endpoints
- `POST /api/dossier/analyze-with-dossier` - Analyze + generate report
- `GET /api/dossier/report/{id}` - Download stored dossier
- `POST /api/dossier/comparative-dossier` - Multi-platform comparison

### Monitoring Endpoints
- `POST /api/analysis/monitoring/repository` - Enable monitoring
- `GET /api/analysis/monitoring/repository` - Check monitoring status
- `WebSocket /ws/live-feed` - Real-time updates

## 🎯 Use Cases

### Civic Technology Assessment
Analyze accountability platforms for:
- Cryptographic verification implementation
- Evidence trail completeness
- Documentation accuracy
- Trust boundary identification

### Software Credibility Review
Evaluate systems for:
- Claims vs implementation alignment
- Security mechanism detection
- Architecture pattern analysis
- Institutional suitability assessment

### Educational Analysis
Learn from real systems:
- Evidence-first design patterns
- Cryptographic verification systems
- Civic technology architecture
- Trust and transparency mechanisms

## 🚨 Limitations

- **Heuristic detection:** Cryptographic and contradiction detection uses pattern matching - signals for review, not definitive verdicts
- **Python focus:** Enhanced parsing currently limited to Python (JavaScript/TypeScript support planned)
- **Documentation dependent:** Claims extraction quality depends on documentation completeness
- **Manual verification recommended:** High-stakes decisions should include expert code review

## 🤝 Community

Code View was built for the civic accountability community:

- **Open source** for transparency and verification
- **Evidence-first approach** for institutional credibility  
- **Educational focus** for knowledge sharing
- **Professional standards** for external review

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Built with the civic accountability community's need for transparent, verifiable software analysis that can withstand adversarial scrutiny while providing educational value about evidence-first system design.

---

**Code View: Forensic analysis for software that matters.**

*"Show me the evidence, not the claims."*
