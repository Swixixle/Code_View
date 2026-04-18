import React, { useState, useEffect, useCallback } from "react";
import {
  ChevronRight,
  Search,
  Code,
  Shield,
  FileText,
  GitBranch,
  Clock,
  AlertTriangle,
  CheckCircle,
  Eye,
  Download,
  Zap,
} from "lucide-react";

const api = (path) => path;

const CodeViewDashboard = () => {
  const [analyses, setAnalyses] = useState([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [liveEvents, setLiveEvents] = useState([]);

  const fetchAnalyses = useCallback(async () => {
    try {
      const response = await fetch(api("/api/analysis/analyses?limit=20"));
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json();
      setAnalyses(data.analyses || []);
    } catch (error) {
      console.error("Failed to fetch analyses:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/live-feed`);

    ws.onopen = () => {
      ws.send("ping");
    };

    ws.onmessage = (event) => {
      const raw = event.data;
      if (typeof raw !== "string") return;
      if (raw === "pong") return;
      let data;
      try {
        data = JSON.parse(raw);
      } catch {
        return;
      }
      if (data.type === "analysis_completed") {
        setLiveEvents((prev) => [data, ...prev.slice(0, 4)]);
        fetchAnalyses();
      }
    };

    return () => {
      ws.close();
    };
  }, [fetchAnalyses]);

  const searchEvidence = async (query) => {
    if (!query.trim()) {
      setEvidence([]);
      return;
    }
    try {
      const response = await fetch(
        api(
          `/api/analysis/evidence/search?query=${encodeURIComponent(query)}&limit=50`
        )
      );
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json();
      setEvidence(data.evidence || []);
    } catch (error) {
      console.error("Failed to search evidence:", error);
    }
  };

  const loadAnalysis = async (analysisId) => {
    try {
      const response = await fetch(api(`/api/analysis/${analysisId}/summary`));
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json();
      setSelectedAnalysis(data);
    } catch (error) {
      console.error("Failed to load analysis:", error);
    }
  };

  const generateDossier = async (analysisId) => {
    try {
      const response = await fetch(api(`/api/dossier/report/${analysisId}`));
      if (!response.ok) throw new Error(String(response.status));
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `forensic_dossier_${analysisId}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to generate dossier:", error);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, [fetchAnalyses]);

  useEffect(() => {
    const delayedSearch = setTimeout(() => {
      searchEvidence(searchQuery);
    }, 300);
    return () => clearTimeout(delayedSearch);
  }, [searchQuery]);

  const stagesDone = selectedAnalysis?.stages_completed || [];
  const stagesFail = selectedAnalysis?.stages_failed || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-blue-500">
                <Eye className="h-5 w-5 text-slate-900" />
              </div>
              <div>
                <h1 className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-xl font-bold text-transparent">
                  Code View
                </h1>
                <p className="text-xs text-slate-400">Evidence-backed code dissection</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="h-2 w-2 animate-pulse rounded-full bg-green-400" />
              <span className="text-sm text-slate-400">Live feed connected</span>
            </div>
          </div>
        </div>
      </header>

      {liveEvents.length > 0 && (
        <div className="border-b border-cyan-800/30 bg-gradient-to-r from-cyan-900/20 to-blue-900/20">
          <div className="mx-auto max-w-7xl px-6 py-2">
            <div className="flex items-center space-x-2 text-sm">
              <Zap className="h-4 w-4 text-cyan-400" />
              <span className="font-medium text-cyan-400">Live:</span>
              <span className="text-slate-300">
                {liveEvents[0].type} — {liveEvents[0].repository} (
                {liveEvents[0].evidence_items} evidence items)
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-1">
            <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6 backdrop-blur-sm">
              <h2 className="mb-4 flex items-center text-lg font-semibold text-slate-100">
                <FileText className="mr-2 h-5 w-5 text-cyan-400" />
                Recent analyses
              </h2>

              {loading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="mb-2 h-4 rounded bg-slate-700" />
                      <div className="h-3 w-3/4 rounded bg-slate-700" />
                    </div>
                  ))}
                </div>
              ) : analyses.length === 0 ? (
                <p className="text-sm text-slate-400">
                  No stored analyses yet. Run{" "}
                  <code className="rounded bg-slate-700 px-1 font-mono text-cyan-300">
                    POST /api/analysis/analyze
                  </code>{" "}
                  with{" "}
                  <code className="rounded bg-slate-700 px-1 font-mono text-cyan-300">
                    persist: true
                  </code>
                  .
                </p>
              ) : (
                <div className="space-y-2">
                  {analyses.map((analysis) => (
                    <div
                      key={analysis.analysis_id}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ")
                          loadAnalysis(analysis.analysis_id);
                      }}
                      className={`cursor-pointer rounded-lg border p-3 transition-all duration-200 ${
                        selectedAnalysis?.analysis_id === analysis.analysis_id
                          ? "border-cyan-700 bg-cyan-900/30"
                          : "border-transparent bg-slate-700/30 hover:bg-slate-700/50"
                      }`}
                      onClick={() => loadAnalysis(analysis.analysis_id)}
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-slate-200">
                          {analysis.repository_url.split("/").pop()}
                        </span>
                        <ChevronRight className="h-4 w-4 text-slate-400" />
                      </div>
                      <div className="flex items-center space-x-4 text-xs text-slate-400">
                        <span className="flex items-center">
                          <Code className="mr-1 h-3 w-3" />
                          {analysis.evidence_count}
                        </span>
                        <span className="flex items-center">
                          <GitBranch className="mr-1 h-3 w-3" />
                          {(analysis.commit_hash || "").slice(0, 7) || "—"}
                        </span>
                        <span className="flex items-center">
                          <Clock className="mr-1 h-3 w-3" />
                          {new Date(analysis.analysis_started).toLocaleDateString()}
                        </span>
                      </div>
                      {analysis.contradictions_count > 0 && (
                        <div className="mt-2 flex items-center text-xs text-amber-400">
                          <AlertTriangle className="mr-1 h-3 w-3" />
                          {analysis.contradictions_count} contradictions
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6 lg:col-span-2">
            {selectedAnalysis && (
              <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6 backdrop-blur-sm">
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-bold text-slate-100">
                      {selectedAnalysis.repository_url.split("/").pop()}
                    </h3>
                    <p className="mt-1 text-sm text-slate-400">
                      Analysis ID: {selectedAnalysis.analysis_id}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => generateDossier(selectedAnalysis.analysis_id)}
                    className="flex items-center space-x-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-white transition-all duration-200 hover:from-cyan-500 hover:to-blue-500"
                  >
                    <Download className="h-4 w-4" />
                    <span>Download dossier</span>
                  </button>
                </div>

                <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                  <div className="rounded-lg bg-slate-700/30 p-4 text-center">
                    <div className="text-2xl font-bold text-cyan-400">
                      {selectedAnalysis.evidence_items}
                    </div>
                    <div className="text-xs text-slate-400">Evidence items</div>
                  </div>
                  <div className="rounded-lg bg-slate-700/30 p-4 text-center">
                    <div className="text-2xl font-bold text-blue-400">
                      {selectedAnalysis.claims_assembled}
                    </div>
                    <div className="text-xs text-slate-400">Claims</div>
                  </div>
                  <div className="rounded-lg bg-slate-700/30 p-4 text-center">
                    <div className="text-2xl font-bold text-amber-400">
                      {selectedAnalysis.contradictions}
                    </div>
                    <div className="text-xs text-slate-400">Contradictions</div>
                  </div>
                  <div className="rounded-lg bg-slate-700/30 p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">
                      {typeof selectedAnalysis.coverage_percentage === "number"
                        ? `${selectedAnalysis.coverage_percentage.toFixed(0)}%`
                        : "—"}
                    </div>
                    <div className="text-xs text-slate-400">Coverage</div>
                  </div>
                </div>

                <div className="mb-6">
                  <h4 className="mb-3 text-sm font-medium text-slate-300">Analysis pipeline</h4>
                  <div className="flex flex-wrap gap-2">
                    {stagesDone.map((stage) => (
                      <div
                        key={stage}
                        className="flex items-center space-x-1 rounded-full bg-green-900/30 px-3 py-1 text-xs text-green-400"
                      >
                        <CheckCircle className="h-3 w-3" />
                        <span>{stage.replace(/_/g, " ")}</span>
                      </div>
                    ))}
                    {stagesFail.map((stage) => (
                      <div
                        key={stage}
                        className="flex items-center space-x-1 rounded-full bg-red-900/30 px-3 py-1 text-xs text-red-400"
                      >
                        <AlertTriangle className="h-3 w-3" />
                        <span>{String(stage).replace(/_/g, " ")}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6 backdrop-blur-sm">
              <div className="mb-4 flex items-center space-x-3">
                <Search className="h-5 w-5 text-cyan-400" />
                <h3 className="text-lg font-semibold text-slate-100">Evidence search</h3>
              </div>

              <div className="relative mb-4">
                <input
                  type="text"
                  placeholder="Search (min 3 chars): crypto, ed25519, sign, pattern…"
                  className="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-3 text-slate-100 placeholder-slate-400 transition-colors focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <Search className="absolute right-3 top-3.5 h-4 w-4 text-slate-400" />
              </div>

              <div className="max-h-96 space-y-3 overflow-y-auto">
                {evidence.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-lg border border-slate-600/50 bg-slate-700/30 p-4"
                  >
                    <div className="mb-2 flex items-start justify-between">
                      <span className="text-sm font-medium text-slate-200">{item.claim}</span>
                      <div className="flex items-center space-x-2">
                        <span
                          className={`rounded-full px-2 py-1 text-xs ${
                            item.confidence === "high"
                              ? "bg-green-900/30 text-green-400"
                              : item.confidence === "medium"
                                ? "bg-yellow-900/30 text-yellow-400"
                                : "bg-red-900/30 text-red-400"
                          }`}
                        >
                          {item.confidence}
                        </span>
                        <span
                          className={`rounded-full px-2 py-1 text-xs ${
                            item.status === "supported"
                              ? "bg-green-900/30 text-green-400"
                              : item.status === "contradicted"
                                ? "bg-red-900/30 text-red-400"
                                : "bg-slate-600/30 text-slate-400"
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>
                    </div>

                    <div className="mb-2 text-xs text-slate-400">
                      <span className="font-medium">Stage:</span>{" "}
                      {String(item.analysis_stage || "").replace(/_/g, " ")} •
                      <span className="ml-2 font-medium">Type:</span> {item.evidence_type}
                    </div>

                    {item.source_locations && item.source_locations.length > 0 && (
                      <div className="flex items-center space-x-2 text-xs">
                        <Code className="h-3 w-3 text-cyan-400" />
                        <span className="font-mono text-cyan-400">
                          {item.source_locations[0].file_path}:{item.source_locations[0].line_start}
                        </span>
                      </div>
                    )}
                  </div>
                ))}

                {searchQuery.length >= 3 && evidence.length === 0 && (
                  <div className="py-8 text-center text-slate-400">
                    <Search className="mx-auto mb-2 h-8 w-8 opacity-50" />
                    <p>No evidence for &quot;{searchQuery}&quot;</p>
                  </div>
                )}

                {searchQuery.length > 0 && searchQuery.length < 3 && (
                  <div className="py-6 text-center text-sm text-slate-500">
                    Enter at least 3 characters to search.
                  </div>
                )}

                {searchQuery.length === 0 && (
                  <div className="py-8 text-center text-slate-400">
                    <Shield className="mx-auto mb-2 h-8 w-8 opacity-50" />
                    <p>Search persisted evidence by claim text</p>
                    <p className="mt-1 text-xs">Try: crypto, sign, verify, pattern</p>
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
