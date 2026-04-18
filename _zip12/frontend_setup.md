# Code View - React Frontend Setup

## Frontend Components Created

1. **`CodeViewDashboard.jsx`** - Main dashboard with forensic analysis interface
2. **`App.jsx`** - React app entry point
3. **`package.json`** - Dependencies and scripts
4. **`vite.config.js`** - Development server with API proxy
5. **`tailwind.config.js`** - Tailwind CSS configuration
6. **`styles.css`** - Custom styling with forensic theme
7. **`index.html`** - HTML template
8. **`index.jsx`** - React entry point

## Frontend Directory Structure

```
/Users/alexmaksimovich/Code_View/frontend/
├── package.json
├── vite.config.js
├── tailwind.config.js
├── index.html
└── src/
    ├── index.jsx
    ├── App.jsx
    ├── CodeViewDashboard.jsx
    └── styles.css
```

## Setup Instructions

### 1. Create Frontend Directory
```bash
mkdir -p /Users/alexmaksimovich/Code_View/frontend/src
cd /Users/alexmaksimovich/Code_View/frontend
```

### 2. Copy Frontend Files
```bash
# Copy package.json
cp frontend_package.json /Users/alexmaksimovich/Code_View/frontend/package.json

# Copy configuration files
cp vite.config.js /Users/alexmaksimovich/Code_View/frontend/
cp tailwind.config.js /Users/alexmaksimovich/Code_View/frontend/
cp index.html /Users/alexmaksimovich/Code_View/frontend/

# Copy React components
cp index.jsx /Users/alexmaksimovich/Code_View/frontend/src/
cp App.jsx /Users/alexmaksimovich/Code_View/frontend/src/
cp CodeViewDashboard.jsx /Users/alexmaksimovich/Code_View/frontend/src/
cp styles.css /Users/alexmaksimovich/Code_View/frontend/src/
```

### 3. Install Dependencies
```bash
cd /Users/alexmaksimovich/Code_View/frontend
npm install
```

### 4. Start Development Server
```bash
npm run dev
```

The frontend will be available at: **http://localhost:3000**

## Frontend Features

### Forensic Analysis Dashboard
- **Live monitoring** with WebSocket connection to backend
- **Analysis list** showing recent forensic examinations
- **Evidence search** with real-time filtering
- **Analysis details** with metrics and pipeline status
- **Dossier generation** with one-click download

### Dark Forensic Theme
- **Slate color palette** with cyan/blue accents
- **Gradient backgrounds** creating depth and atmosphere
- **Monospace font** for code references
- **Animated indicators** for live status
- **Smooth transitions** and hover effects

### Live Features
- **WebSocket connection** to `/ws/live-feed` endpoint
- **Real-time notifications** when analyses complete
- **Live status indicator** showing monitoring activity
- **Event ticker** displaying recent analysis activity

### Evidence Visualization
- **Interactive search** across all evidence items
- **Confidence levels** with color coding (high/medium/low)
- **Evidence status** indicators (supported/contradicted/unknown)
- **Source location** links with file paths and line numbers
- **Analysis stage** categorization

### Analysis Management
- **Repository selection** from recent analyses
- **Detailed metrics** (evidence count, claims, contradictions, coverage)
- **Pipeline visualization** showing completed/failed stages
- **One-click dossier generation** with automatic download

## API Integration

The frontend connects to your Code View backend:

### REST API Calls
- `GET /api/analysis/analyses` - Fetch recent analyses
- `GET /api/analysis/{id}/summary` - Get analysis details
- `GET /api/analysis/evidence/search` - Search evidence
- `GET /api/dossier/report/{id}` - Download dossier

### WebSocket Connection
- `ws://localhost:8000/ws/live-feed` - Live monitoring events
- Real-time analysis completion notifications
- Live event ticker with evidence counts

## Development Workflow

### Start Both Services
```bash
# Terminal 1 - Backend
cd /Users/alexmaksimovich/Code_View/backend
.venv/bin/uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend  
cd /Users/alexmaksimovich/Code_View/frontend
npm run dev
```

### Testing the Complete System
1. **Visit http://localhost:3000** to see the dashboard
2. **Backend analyses** automatically appear in the frontend list
3. **Search for evidence** using terms like "crypto", "ed25519", "sign"
4. **Select an analysis** to view detailed metrics
5. **Generate dossiers** with one-click download

## Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## What You Now Have

**Complete forensic analysis platform:**
- ✅ **Backend API** with evidence extraction and persistence
- ✅ **Live monitoring** with WebSocket updates  
- ✅ **Educational dossiers** with comprehensive reports
- ✅ **React frontend** with forensic analysis dashboard
- ✅ **Evidence visualization** with search and filtering
- ✅ **One-click dossier generation** and download

**The frontend transforms Code View from a backend service into a complete forensic analysis platform** with an intuitive interface for exploring evidence, generating reports, and monitoring civic accountability platforms.
