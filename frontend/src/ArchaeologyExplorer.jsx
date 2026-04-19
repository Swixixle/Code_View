import React, { useCallback, useEffect, useState } from "react";

const api = (path) => path;

const TRACE_KEYS = [
  ["callers", "Callers"],
  ["callees", "Callees"],
  ["imports", "Imports"],
  ["imported_by", "Imported by"],
  ["contains", "Contains"],
  ["contained_by", "Contained by"],
];

const EVIDENCE_GROUPS = [
  "code_definition",
  "code_relation",
  "git_history",
  "documentation_claim",
  "keyword_heuristic",
];

function traceHasAnyEdges(traceData) {
  if (!traceData) return false;
  return TRACE_KEYS.some(([k]) => (traceData[k] || []).length > 0);
}

function groupEvidenceItems(items) {
  const buckets = Object.fromEntries(EVIDENCE_GROUPS.map((g) => [g, []]));
  buckets.other = [];
  for (const it of items || []) {
    const sc = it.source_class || "keyword_heuristic";
    if (buckets[sc]) buckets[sc].push(it);
    else buckets.other.push(it);
  }
  return buckets;
}

function collectUncertaintyNotes({ traceData, interpretData }) {
  const notes = [];
  if (interpretData?.archaeological_gaps?.length) {
    notes.push(...interpretData.archaeological_gaps);
  }
  if (interpretData?.history_precision === "file") {
    notes.push(
      "history_precision is file: commits may not have edited this exact line span."
    );
  }
  if (traceData && !traceHasAnyEdges(traceData)) {
    notes.push("No trace edges found (static graph only; empty ≠ absent at runtime).");
  }
  return [...new Set(notes)];
}

function Section({ title, children, className = "" }) {
  return (
    <section
      className={`mb-6 rounded-lg border border-slate-800 bg-slate-900/50 p-3 ${className}`}
    >
      <h2 className="mb-2 border-b border-slate-800 pb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      {children}
    </section>
  );
}

export default function ArchaeologyExplorer() {
  const [repoInput, setRepoInput] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [identifyData, setIdentifyData] = useState(null);
  const [traceData, setTraceData] = useState(null);
  const [interpretData, setInterpretData] = useState(null);
  const [entityEvidence, setEntityEvidence] = useState([]);
  const [relationData, setRelationData] = useState(null);
  const [loading, setLoading] = useState({
    analyze: false,
    panels: false,
    evidence: false,
    relation: false,
  });
  const [error, setError] = useState(null);

  const analysisId = analysis?.analysis_id ?? "";
  const interpretRepoPath =
    repoInput.trim() && !repoInput.trim().startsWith("http")
      ? repoInput.trim()
      : "";

  const setLoad = (key, v) =>
    setLoading((prev) => ({ ...prev, [key]: v }));

  const runAnalyze = async () => {
    const source = repoInput.trim();
    if (!source) {
      setError("Enter a repository path or Git URL.");
      return;
    }
    setError(null);
    setLoad("analyze", true);
    setAnalysis(null);
    setSearchResults([]);
    setSelectedEntity(null);
    setIdentifyData(null);
    setTraceData(null);
    setInterpretData(null);
    setEntityEvidence([]);
    setRelationData(null);
    try {
      const res = await fetch(api("/api/analysis/analyze"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source,
          persist: true,
          run_archaeology: true,
        }),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t.slice(0, 500) || String(res.status));
      }
      const data = await res.json();
      setAnalysis({
        analysis_id: data.analysis_id,
        repository_url: data.repository_url,
        commit_hash: data.commit_hash,
        repo_id: data.repo_id,
        archaeology: data.archaeology,
      });
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoad("analyze", false);
    }
  };

  const runSearch = useCallback(async () => {
    const q = searchQuery.trim();
    if (!analysisId || !q) {
      setSearchResults([]);
      return;
    }
    setError(null);
    try {
      const qs = new URLSearchParams({
        q,
        analysis_id: analysisId,
        limit: "80",
      });
      const res = await fetch(
        api(`/api/analysis/entities/search?${qs.toString()}`)
      );
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSearchResults(data.entities || []);
    } catch (e) {
      setError(e.message || String(e));
      setSearchResults([]);
    }
  }, [searchQuery, analysisId]);

  useEffect(() => {
    const t = setTimeout(runSearch, 300);
    return () => clearTimeout(t);
  }, [runSearch]);

  const loadEntityBundle = async (entity) => {
    if (!entity?.entity_id) return;
    setError(null);
    setLoad("panels", true);
    setLoad("evidence", true);
    setRelationData(null);
    const id = encodeURIComponent(entity.entity_id);
    const interpretQs = interpretRepoPath
      ? `?repo_path=${encodeURIComponent(interpretRepoPath)}`
      : "";
    let panelsOk = false;
    try {
      const [rId, rTr, rIn] = await Promise.all([
        fetch(api(`/api/analysis/entity/${id}/identify`)),
        fetch(api(`/api/analysis/entity/${id}/trace`)),
        fetch(api(`/api/analysis/entity/${id}/interpret${interpretQs}`)),
      ]);
      if (!rId.ok) throw new Error(await rId.text());
      if (!rTr.ok) throw new Error(await rTr.text());
      if (!rIn.ok) throw new Error(await rIn.text());
      const [jId, jTr, jIn] = await Promise.all([
        rId.json(),
        rTr.json(),
        rIn.json(),
      ]);
      setIdentifyData(jId);
      setTraceData(jTr);
      setInterpretData(jIn);
      panelsOk = true;
    } catch (e) {
      setIdentifyData(null);
      setTraceData(null);
      setInterpretData(null);
      setEntityEvidence([]);
      setError(e.message || String(e));
    } finally {
      setLoad("panels", false);
    }

    if (!panelsOk || !analysisId) {
      if (!analysisId) setEntityEvidence([]);
      setLoad("evidence", false);
      return;
    }
    try {
      const qs = new URLSearchParams({ analysis_id: analysisId });
      const rEv = await fetch(
        api(`/api/analysis/entity/${id}/evidence?${qs.toString()}`)
      );
      if (!rEv.ok) {
        const t = await rEv.text();
        throw new Error(t);
      }
      const jEv = await rEv.json();
      setEntityEvidence(jEv.items || []);
    } catch (e) {
      setEntityEvidence([]);
      setError((prev) => prev || e.message || String(e));
    } finally {
      setLoad("evidence", false);
    }
  };

  const selectEntity = (row) => {
    setSelectedEntity(row);
    loadEntityBundle(row);
  };

  const openPeerEntity = (peerId) => {
    if (!peerId) return;
    const known =
      searchResults.find((e) => e.entity_id === peerId) ||
      (selectedEntity?.entity_id === peerId ? selectedEntity : null);
    const stub = known || {
      entity_id: peerId,
      symbol_name: peerId,
      qualified_name: "—",
      entity_kind: "",
      file_path: "",
      line_span: {},
    };
    selectEntity(stub);
  };

  const openRelation = async (relationId) => {
    if (!relationId) return;
    setError(null);
    setLoad("relation", true);
    setRelationData(null);
    try {
      const qs = analysisId
        ? `?analysis_id=${encodeURIComponent(analysisId)}`
        : "";
      const res = await fetch(
        api(`/api/analysis/relation/${encodeURIComponent(relationId)}${qs}`)
      );
      if (!res.ok) throw new Error(await res.text());
      setRelationData(await res.json());
    } catch (e) {
      setRelationData({ error: e.message || String(e) });
    } finally {
      setLoad("relation", false);
    }
  };

  const uncertaintyNotes = collectUncertaintyNotes({ traceData, interpretData });
  const evidenceBuckets = groupEvidenceItems(entityEvidence);
  const docOnlySignals = (entityEvidence || []).filter(
    (x) =>
      x.refinement_signal === "doc_only_claim" ||
      (x.source_class === "documentation_claim" && x.derived_from_doc)
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <div className="mx-auto flex max-w-[1900px] gap-4 px-4 py-4">
        <aside className="w-80 shrink-0 space-y-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-3">
            <label className="text-xs text-slate-500" htmlFor="repo">
              Repository (path or URL)
            </label>
            <input
              id="repo"
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-xs text-slate-200"
              value={repoInput}
              onChange={(e) => setRepoInput(e.target.value)}
              placeholder="/path/to/repo"
            />
            <button
              type="button"
              className="mt-2 w-full rounded bg-slate-700 py-1.5 text-sm text-slate-100 hover:bg-slate-600 disabled:opacity-50"
              onClick={runAnalyze}
              disabled={loading.analyze}
            >
              {loading.analyze ? "Analyzing…" : "Analyze"}
            </button>
            {analysis ? (
              <p className="mt-2 break-all font-mono text-[10px] text-slate-500">
                analysis_id: {analysis.analysis_id}
                {analysis.archaeology?.skipped
                  ? ` · archaeology skipped (${analysis.archaeology.reason || "?"})`
                  : ""}
              </p>
            ) : (
              <p className="mt-2 text-xs text-slate-600">
                Run analyze to set analysis_id for search and evidence.
              </p>
            )}
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-3">
            <label className="text-xs text-slate-500" htmlFor="search">
              Entity search
            </label>
            <input
              id="search"
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              disabled={!analysisId}
              placeholder="symbol or path…"
            />
            <ul className="mt-2 max-h-[48vh] space-y-1 overflow-y-auto">
              {searchResults.map((e) => (
                <li key={e.entity_id}>
                  <button
                    type="button"
                    className={`w-full rounded border px-2 py-1.5 text-left text-xs ${
                      selectedEntity?.entity_id === e.entity_id
                        ? "border-cyan-700 bg-cyan-950/50 ring-1 ring-cyan-800"
                        : "border-transparent bg-slate-950/50 hover:border-slate-700"
                    }`}
                    onClick={() => selectEntity(e)}
                  >
                    <div>
                      <span className="font-medium text-slate-100">
                        {e.symbol_name}
                      </span>{" "}
                      <span className="text-slate-500">{e.entity_kind}</span>
                    </div>
                    <div className="truncate font-mono text-[10px] text-slate-500">
                      {e.qualified_name}
                    </div>
                    <div className="font-mono text-[10px] text-slate-600">
                      {e.file_path}
                      {e.line_span?.start_line != null
                        ? ` :${e.line_span.start_line}–${e.line_span.end_line ?? e.line_span.start_line}`
                        : ""}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
            {analysisId && searchQuery && searchResults.length === 0 ? (
              <p className="mt-2 text-xs text-slate-600">No matches.</p>
            ) : null}
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 gap-4">
          <main className="min-w-0 flex-1 space-y-2 overflow-y-auto rounded-lg border border-slate-800 bg-slate-900/40 p-4">
            {error ? (
              <p className="text-sm text-red-400">{error}</p>
            ) : null}
            {(loading.panels || loading.evidence) && selectedEntity ? (
              <p className="text-xs text-slate-500">
                Loading entity data…
              </p>
            ) : null}

            {!selectedEntity ? (
              <p className="text-sm text-slate-600">
                Select an entity from the list.
              </p>
            ) : (
              <>
                {uncertaintyNotes.length > 0 || docOnlySignals.length > 0 ? (
                  <div className="mb-4 rounded border border-amber-900/40 bg-amber-950/20 p-2 text-xs text-amber-200/90">
                    <div className="font-medium text-amber-400/90">Notes / gaps</div>
                    <ul className="mt-1 list-inside list-disc text-amber-200/80">
                      {uncertaintyNotes.map((n) => (
                        <li key={n}>{n}</li>
                      ))}
                    </ul>
                    {docOnlySignals.length > 0 ? (
                      <p className="mt-2 text-amber-200/70">
                        Some linked items are documentation-class; compare to code
                        and git rows below.
                      </p>
                    ) : null}
                  </div>
                ) : null}

                <Section title="1. Identity">
                  {identifyData ? (
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="text-slate-500">symbol</span>{" "}
                        <span className="text-slate-100">
                          {identifyData.symbol_name}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">kind</span>{" "}
                        {identifyData.entity_kind}
                      </div>
                      <div className="break-all font-mono text-xs text-slate-400">
                        {identifyData.qualified_name}
                      </div>
                      <div className="font-mono text-xs text-slate-500">
                        {identifyData.file_path} (
                        {identifyData.line_span?.start_line}–
                        {identifyData.line_span?.end_line})
                      </div>
                      <div className="break-all font-mono text-[10px] text-slate-600">
                        {identifyData.entity_id}
                      </div>
                      <div className="font-mono text-[10px] text-slate-600">
                        repo_id {identifyData.repo_id} · commit{" "}
                        {(identifyData.commit_sha || "").slice(0, 12)}…
                      </div>
                      {identifyData.docstring ? (
                        <div className="mt-2 rounded border border-slate-800 bg-slate-950/60 p-2 text-xs text-slate-400">
                          <span className="text-slate-600">docstring</span>
                          <pre className="mt-1 whitespace-pre-wrap font-mono text-[11px] text-slate-300">
                            {identifyData.docstring}
                          </pre>
                        </div>
                      ) : (
                        <p className="text-xs text-slate-600">No docstring.</p>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-600">No identify data.</p>
                  )}
                </Section>

                <Section title="2. Source context">
                  {identifyData?.source_context ? (
                    <div className="text-sm">
                      <p className="font-mono text-xs text-slate-500">
                        {identifyData.source_context.file_path} (
                        {identifyData.source_context.line_span?.start_line}–
                        {identifyData.source_context.line_span?.end_line})
                      </p>
                      {identifyData.source_context.snippet ? (
                        <>
                          {identifyData.source_context.snippet_truncated ? (
                            <p className="mt-1 text-[10px] text-slate-600">
                              Snippet truncated (compare full file locally).
                            </p>
                          ) : null}
                          <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded border border-slate-800 bg-slate-950 p-2 font-mono text-[11px] text-slate-300">
                            {identifyData.source_context.snippet}
                          </pre>
                        </>
                      ) : (
                        <p className="mt-2 text-xs text-slate-600">
                          No indexed source snippet for this entity (raw_content empty in store).
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-600">
                      Run analyze and select an entity for source context.
                    </p>
                  )}
                </Section>

                <Section title="3. Trace">
                  {!traceData ? (
                    <p className="text-sm text-slate-600">No trace data.</p>
                  ) : !traceHasAnyEdges(traceData) ? (
                    <p className="text-sm text-slate-500">
                      No trace edges found.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-[10px] text-slate-600">
                        {traceData.graph_confidence_summary?.note}
                      </p>
                      {TRACE_KEYS.map(([key, label]) => {
                        const edges = traceData[key] || [];
                        if (!edges.length) return null;
                        return (
                          <div key={key}>
                            <h3 className="mb-1 text-xs font-medium text-slate-500">
                              {label}
                            </h3>
                            <ul className="space-y-2">
                              {edges.map((edge) => (
                                <li
                                  key={`${edge.relation_id}-${edge.peer_entity_id}`}
                                >
                                  <div className="rounded border border-slate-800 bg-slate-950/80 p-2 text-xs">
                                    <button
                                      type="button"
                                      className="w-full text-left"
                                      onClick={() =>
                                        openRelation(edge.relation_id)
                                      }
                                    >
                                      <div className="flex flex-wrap gap-x-2 gap-y-1 text-[10px] text-slate-500">
                                        <span>{edge.relation_type}</span>
                                        {edge.confidence &&
                                        edge.confidence !== "high" ? (
                                          <span className="text-amber-600/90">
                                            confidence: {edge.confidence}
                                          </span>
                                        ) : (
                                          <span>{edge.confidence}</span>
                                        )}
                                        {edge.provenance_label ? (
                                          <span>{edge.provenance_label}</span>
                                        ) : null}
                                        {edge.source_class ? (
                                          <span>· {edge.source_class}</span>
                                        ) : null}
                                      </div>
                                      <div className="mt-1 font-mono text-slate-200">
                                        {edge.peer_symbol_name ||
                                          edge.peer_qualified_name ||
                                          edge.peer_entity_id}
                                      </div>
                                      <div className="font-mono text-[10px] text-slate-500">
                                        {edge.peer_qualified_name}
                                      </div>
                                      <div className="font-mono text-[10px] text-slate-600">
                                        {edge.peer_file_path}
                                        {edge.peer_line_span
                                          ? ` :${edge.peer_line_span.start_line}–${edge.peer_line_span.end_line}`
                                          : ""}
                                      </div>
                                      <div className="mt-1 font-mono text-[10px] text-cyan-800">
                                        {edge.relation_id}
                                      </div>
                                    </button>
                                    <button
                                      type="button"
                                      className="mt-1 text-[10px] text-cyan-600 hover:underline"
                                      onClick={() =>
                                        openPeerEntity(edge.peer_entity_id)
                                      }
                                    >
                                      Open peer entity
                                    </button>
                                  </div>
                                </li>
                              ))}
                            </ul>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Section>

                <Section title="4. History (interpret)">
                  {!interpretData ? (
                    <p className="text-sm text-slate-600">No interpret data.</p>
                  ) : (
                    <>
                      <div className="mb-2 text-xs text-slate-500">
                        history_precision:{" "}
                        <code
                          className={
                            interpretData.history_precision === "line"
                              ? "text-cyan-400"
                              : "text-slate-400"
                          }
                        >
                          {interpretData.history_precision || "—"}
                        </code>
                        {interpretData.history_precision === "file" ? (
                          <span className="ml-2 text-amber-700/90">
                            (weaker than line-scoped)
                          </span>
                        ) : null}
                      </div>
                      {interpretData.history_notes?.length ? (
                        <ul className="mb-2 list-inside list-disc text-xs text-slate-500">
                          {interpretData.history_notes.map((n) => (
                            <li key={n}>{n}</li>
                          ))}
                        </ul>
                      ) : null}
                      {!interpretRepoPath ? (
                        <p className="text-xs text-slate-600">
                          Use a local directory in Repository above for git
                          history.
                        </p>
                      ) : null}
                      {interpretData.observed_evolution &&
                      interpretData.observed_evolution.length > 0 ? (
                        <ul className="space-y-2 text-xs">
                          {interpretData.observed_evolution.map((row, i) => (
                            <li
                              key={`${row.commit_sha || i}-${i}`}
                              className={`rounded border p-2 ${
                                row.history_precision === "file" ||
                                interpretData.history_precision === "file"
                                  ? "border-slate-800 bg-slate-950/40 opacity-90"
                                  : "border-slate-700 bg-slate-950/70"
                              }`}
                            >
                              <div className="font-mono text-[10px] text-slate-500">
                                {row.commit_sha?.slice(0, 12)}… ·{" "}
                                {row.source_class || "git_history"} ·{" "}
                                {row.provenance_label || "git history"}
                              </div>
                              <div className="text-slate-200">{row.subject}</div>
                              <div className="text-slate-500">
                                {row.author || row.author_hint}{" "}
                                {row.authored_at ? `· ${row.authored_at}` : ""}
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-slate-500">
                          No git history available for this entity.
                        </p>
                      )}
                      {interpretData.documented_intent?.length ? (
                        <div className="mt-4 opacity-70">
                          <h4 className="text-[10px] font-medium uppercase text-slate-600">
                            Documented intent (secondary)
                          </h4>
                          <ul className="mt-1 space-y-1 text-xs text-slate-500">
                            {interpretData.documented_intent.map((d, i) => (
                              <li key={i} className="rounded border border-slate-800/80 p-2">
                                {d.text?.slice(0, 400)}
                                {d.text?.length > 400 ? "…" : ""}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </>
                  )}
                </Section>

                <Section title="5. Evidence (linked)">
                  {loading.evidence ? (
                    <p className="text-xs text-slate-500">Loading evidence…</p>
                  ) : !analysisId ? (
                    <p className="text-sm text-slate-600">
                      Analyze with persist to link evidence to analysis_id.
                    </p>
                  ) : entityEvidence.length === 0 ? (
                    <p className="text-sm text-slate-500">
                      No evidence rows linked to this entity (linked_entity_ids /
                      linked_relation_ids).
                    </p>
                  ) : (
                    <div className="space-y-4">
                      {[...EVIDENCE_GROUPS, "other"].map((g) => {
                        const items = evidenceBuckets[g] || [];
                        if (!items.length) return null;
                        const isDoc = g === "documentation_claim";
                        return (
                          <div
                            key={g}
                            className={
                              isDoc ? "opacity-75" : ""
                            }
                          >
                            <h3 className="mb-1 text-xs font-medium text-slate-500">
                              {g.replace(/_/g, " ")}
                              {isDoc ? " (secondary)" : ""}
                            </h3>
                            <ul className="space-y-2">
                              {items.map((it) => (
                                <li
                                  key={it.id}
                                  className="rounded border border-slate-800 bg-slate-950/50 p-2 text-xs"
                                >
                                  <div className="text-slate-300">
                                    {it.claim}
                                  </div>
                                  <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-slate-500">
                                    <span>{it.source_class}</span>
                                    <span>{it.provenance_label}</span>
                                    <span>confidence: {it.confidence}</span>
                                    {it.refinement_signal ? (
                                      <span>refinement: {it.refinement_signal}</span>
                                    ) : null}
                                  </div>
                                  {it.linked_entity_ids?.length ? (
                                    <div className="mt-1 font-mono text-[10px] text-slate-600">
                                      entities: {it.linked_entity_ids.join(", ")}
                                    </div>
                                  ) : null}
                                  {it.linked_relation_ids?.length ? (
                                    <div className="font-mono text-[10px] text-slate-600">
                                      relations:{" "}
                                      {it.linked_relation_ids.join(", ")}
                                    </div>
                                  ) : null}
                                  {it.source_locations?.length ? (
                                    <pre className="mt-1 max-h-24 overflow-auto text-[10px] text-slate-600">
                                      {JSON.stringify(it.source_locations, null, 2)}
                                    </pre>
                                  ) : null}
                                  {it.boundary_note ? (
                                    <p className="mt-1 text-[10px] text-slate-600">
                                      {it.boundary_note}
                                    </p>
                                  ) : null}
                                </li>
                              ))}
                            </ul>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Section>
              </>
            )}
          </main>

          <aside className="w-80 shrink-0 rounded-lg border border-slate-800 bg-slate-900/80 p-3">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase text-slate-500">
                6. Relation inspector
              </h3>
              {relationData ? (
                <button
                  type="button"
                  className="text-[10px] text-slate-600 hover:text-slate-400"
                  onClick={() => setRelationData(null)}
                >
                  Close
                </button>
              ) : null}
            </div>
            {loading.relation ? (
              <p className="text-xs text-slate-500">Loading…</p>
            ) : null}
            {relationData ? (
              <div className="space-y-3 text-xs">
                {relationData.error ? (
                  <p className="text-red-400">{relationData.error}</p>
                ) : null}
                <div className="font-mono text-[10px] text-slate-500">
                  {relationData.relation_id}
                </div>
                <div>
                  {relationData.relation_type} · {relationData.confidence}
                </div>
                <div className="text-[10px] text-slate-500">
                  {relationData.source_class} · {relationData.provenance_label}
                </div>
                <div className="grid gap-2">
                  <div className="rounded border border-slate-800 p-2">
                    <div className="text-[10px] text-slate-600">Source</div>
                    <pre className="mt-1 max-h-32 overflow-auto font-mono text-[10px] text-slate-400">
                      {JSON.stringify(relationData.source_entity, null, 2)}
                    </pre>
                    {relationData.source_entity?.entity_id ? (
                      <button
                        type="button"
                        className="mt-1 text-[10px] text-cyan-600 hover:underline"
                        onClick={() =>
                          openPeerEntity(relationData.source_entity.entity_id)
                        }
                      >
                        Open source entity
                      </button>
                    ) : null}
                  </div>
                  <div className="rounded border border-slate-800 p-2">
                    <div className="text-[10px] text-slate-600">Target</div>
                    <pre className="mt-1 max-h-32 overflow-auto font-mono text-[10px] text-slate-400">
                      {JSON.stringify(relationData.target_entity, null, 2)}
                    </pre>
                    {relationData.target_entity?.entity_id ? (
                      <button
                        type="button"
                        className="mt-1 text-[10px] text-cyan-600 hover:underline"
                        onClick={() =>
                          openPeerEntity(relationData.target_entity.entity_id)
                        }
                      >
                        Open target entity
                      </button>
                    ) : null}
                  </div>
                </div>
                {relationData.evidence_json != null ? (
                  <div>
                    <div className="text-[10px] text-slate-600">evidence_json</div>
                    <pre className="mt-1 max-h-40 overflow-auto font-mono text-[10px] text-slate-400">
                      {JSON.stringify(relationData.evidence_json, null, 2)}
                    </pre>
                  </div>
                ) : null}
                {relationData.linked_evidence_ids?.length ? (
                  <div>
                    <div className="text-[10px] text-slate-600">
                      linked_evidence_ids
                    </div>
                    <div className="font-mono text-[10px] text-slate-500">
                      {relationData.linked_evidence_ids.join(", ")}
                    </div>
                  </div>
                ) : (
                  <p className="text-[10px] text-slate-600">
                    No linked_evidence_ids for this analysis.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-600">
                Click a trace row to load relation detail.
              </p>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
