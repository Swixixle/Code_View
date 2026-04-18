import React, { useState, useEffect } from 'react';
import { ChevronRight, Search, Code, Shield, FileText, GitBranch, Clock, AlertTriangle, CheckCircle, Eye, Download, Zap } from 'lucide-react';

const CodeViewDashboard = () => {
  const [analyses, setAnalyses] = useState([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [websocket, setWebsocket] = useState(null);
  const [liveEvents, setLiveEvents] = useState([]);

  // Connect to WebSocket for live updates
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/live-feed');
    
    ws.onopen = () => {
      console.log('Connected to live feed');
      ws.send('ping');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'analysis_completed') {
        setLiveEvents(prev => [data, ...prev.slice(0, 4)]);
        fetchAnalyses(); // Refresh list
      }
    };
    
    setWebsocket(ws);
    
    return () => {
      ws.close();
    };
  }, []);

  // Fetch analyses from API
  const fetchAnalyses = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/analysis/analyses?limit=20');
      const data = await response.json();
      setAnalyses(data.analyses);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch analyses:', error);
      setLoading(false);
    }
  };

  // Search evidence
  const searchEvidence = async (query) => {
    if (!query.trim()) {
      setEvidence([]);
      return;
    }
    
    try {
      const response = await fetch(`http://localhost:8000/api/analysis/evidence/search?query=${encodeURIComponent(query)}&limit=50`);
      const data = await response.json();
      setEvidence(data.evidence);
    } catch (error) {
      console.error('Failed to search evidence:', error);
    }
  };

  // Load analysis details
  const loadAnalysis = async (analysisId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/analysis/${analysisId}/summary`);
      const data = await response.json();
      setSelectedAnalysis(data);
    } catch (error) {
      console.error('Failed to load analysis:', error);
    }
  };

  // Generate dossier
  const generateDossier = async (analysisId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/dossier/report/${analysisId}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `forensic_dossier_${analysisId}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to generate dossier:', error);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, []);

  useEffect(() => {
    const delayedSearch = setTimeout(() => {
      searchEvidence(searchQuery);
    }, 300);
    
    return () => clearTimeout(delayedSearch);
  }, [searchQuery]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-lg flex items-center justify-center">
                <Eye className="w-5 h-5 text-slate-900" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                  Code View
                </h1>
                <p className="text-xs text-slate-400">Evidence-backed code dissection</p>
              </div>
            </div>
            
            {/* Live status indicator */}
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm text-slate-400">Live monitoring active</span>
            </div>
          </div>
        </div>
      </header>

      {/* Live events ticker */}
      {liveEvents.length > 0 && (
        <div className="bg-gradient-to-r from-cyan-900/20 to-blue-900/20 border-b border-cyan-800/30">
          <div className="max-w-7xl mx-auto px-6 py-2">
            <div className="flex items-center space-x-2 text-sm">
              <Zap className="w-4 h-4 text-cyan-400" />
              <span className="text-cyan-400 font-medium">Live:</span>
              <span className="text-slate-300">
                {liveEvents[0].type} - {liveEvents[0].repository} ({liveEvents[0].evidence_items} evidence items)
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Analysis List */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
              <h2 className="text-lg font-semibold text-slate-100 mb-4 flex items-center">
                <FileText className="w-5 h-5 mr-2 text-cyan-400" />
                Recent Analyses
              </h2>
              
              {loading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-slate-700 rounded mb-2"></div>
                      <div className="h-3 bg-slate-700 rounded w-3/4"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {analyses.map((analysis) => (
                    <div
                      key={analysis.analysis_id}
                      className={`p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                        selectedAnalysis?.analysis_id === analysis.analysis_id
                          ? 'bg-cyan-900/30 border border-cyan-700'
                          : 'bg-slate-700/30 hover:bg-slate-700/50 border border-transparent'
                      }`}
                      onClick={() => loadAnalysis(analysis.analysis_id)}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm text-slate-200">
                          {analysis.repository_url.split('/').pop()}
                        </span>
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                      </div>
                      <div className="flex items-center space-x-4 text-xs text-slate-400">
                        <span className="flex items-center">
                          <Code className="w-3 h-3 mr-1" />
                          {analysis.evidence_count}
                        </span>
                        <span className="flex items-center">
                          <GitBranch className="w-3 h-3 mr-1" />
                          {analysis.commit_hash.slice(0, 7)}
                        </span>
                        <span className="flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {new Date(analysis.analysis_started).toLocaleDateString()}
                        </span>
                      </div>
                      {analysis.contradictions_count > 0 && (
                        <div className="mt-2 flex items-center text-xs text-amber-400">
                          <AlertTriangle className="w-3 h-3 mr-1" />
                          {analysis.contradictions_count} contradictions
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Selected Analysis Details */}
            {selectedAnalysis && (
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-xl font-bold text-slate-100">
                      {selectedAnalysis.repository_url.split('/').pop()}
                    </h3>
                    <p className="text-slate-400 text-sm mt-1">
                      Analysis ID: {selectedAnalysis.analysis_id}
                    </p>
                  </div>
                  <button
                    onClick={() => generateDossier(selectedAnalysis.analysis_id)}
                    className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-lg hover:from-cyan-500 hover:to-blue-500 transition-all duration-200"
                  >
                    <Download className="w-4 h-4" />
                    <span>Generate Dossier</span>
                  </button>
                </div>

                {/* Analysis metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-slate-700/30 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-cyan-400">{selectedAnalysis.evidence_items}</div>
                    <div className="text-xs text-slate-400">Evidence Items</div>
                  </div>
                  <div className="bg-slate-700/30 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-blue-400">{selectedAnalysis.claims_assembled}</div>
                    <div className="text-xs text-slate-400">Claims</div>
                  </div>
                  <div className="bg-slate-700/30 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-amber-400">{selectedAnalysis.contradictions}</div>
                    <div className="text-xs text-slate-400">Contradictions</div>
                  </div>
                  <div className="bg-slate-700/30 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">{selectedAnalysis.coverage_percentage.toFixed(0)}%</div>
                    <div className="text-xs text-slate-400">Coverage</div>
                  </div>
                </div>

                {/* Pipeline status */}
                <div className="mb-6">
                  <h4 className="text-sm font-medium text-slate-300 mb-3">Analysis Pipeline</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedAnalysis.stages_completed.map((stage) => (
                      <div key={stage} className="flex items-center space-x-1 px-3 py-1 bg-green-900/30 text-green-400 rounded-full text-xs">
                        <CheckCircle className="w-3 h-3" />
                        <span>{stage.replace(/_/g, ' ')}</span>
                      </div>
                    ))}
                    {selectedAnalysis.stages_failed.map((stage) => (
                      <div key={stage} className="flex items-center space-x-1 px-3 py-1 bg-red-900/30 text-red-400 rounded-full text-xs">
                        <AlertTriangle className="w-3 h-3" />
                        <span>{stage.replace(/_/g, ' ')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Evidence Search */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 p-6">
              <div className="flex items-center space-x-3 mb-4">
                <Search className="w-5 h-5 text-cyan-400" />
                <h3 className="text-lg font-semibold text-slate-100">Evidence Search</h3>
              </div>
              
              <div className="relative mb-4">
                <input
                  type="text"
                  placeholder="Search evidence (e.g., 'crypto', 'ed25519', 'sign', 'pattern')..."
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-100 placeholder-slate-400 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <Search className="absolute right-3 top-3.5 w-4 h-4 text-slate-400" />
              </div>

              {/* Search results */}
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {evidence.map((item) => (
                  <div key={item.id} className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/50">
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-sm font-medium text-slate-200">{item.claim}</span>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          item.confidence === 'high' ? 'bg-green-900/30 text-green-400' :
                          item.confidence === 'medium' ? 'bg-yellow-900/30 text-yellow-400' :
                          'bg-red-900/30 text-red-400'
                        }`}>
                          {item.confidence}
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          item.status === 'supported' ? 'bg-green-900/30 text-green-400' :
                          item.status === 'contradicted' ? 'bg-red-900/30 text-red-400' :
                          'bg-slate-600/30 text-slate-400'
                        }`}>
                          {item.status}
                        </span>
                      </div>
                    </div>
                    
                    <div className="text-xs text-slate-400 mb-2">
                      <span className="font-medium">Stage:</span> {item.analysis_stage.replace(/_/g, ' ')} • 
                      <span className="font-medium ml-2">Type:</span> {item.evidence_type}
                    </div>
                    
                    {item.source_locations && item.source_locations.length > 0 && (
                      <div className="flex items-center space-x-2 text-xs">
                        <Code className="w-3 h-3 text-cyan-400" />
                        <span className="text-cyan-400 font-mono">
                          {item.source_locations[0].file_path}:{item.source_locations[0].line_start}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
                
                {searchQuery && evidence.length === 0 && (
                  <div className="text-center py-8 text-slate-400">
                    <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>No evidence found for "{searchQuery}"</p>
                  </div>
                )}
                
                {!searchQuery && (
                  <div className="text-center py-8 text-slate-400">
                    <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>Enter a search term to explore evidence</p>
                    <p className="text-xs mt-1">Try: crypto, ed25519, sign, verify, pattern</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CodeViewDashboard;