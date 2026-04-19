import React, { useState } from "react";
import CodeViewDashboard from "./CodeViewDashboard.jsx";
import ArchaeologyExplorer from "./ArchaeologyExplorer.jsx";

function App() {
  const [view, setView] = useState("dashboard");

  return (
    <div className="App">
      <nav className="flex gap-2 border-b border-slate-800 bg-slate-950 px-4 py-2 text-sm">
        <button
          type="button"
          className={`rounded px-3 py-1 ${
            view === "dashboard"
              ? "bg-slate-800 text-slate-100"
              : "text-slate-500 hover:text-slate-300"
          }`}
          onClick={() => setView("dashboard")}
        >
          Dashboard
        </button>
        <button
          type="button"
          className={`rounded px-3 py-1 ${
            view === "explorer"
              ? "bg-slate-800 text-slate-100"
              : "text-slate-500 hover:text-slate-300"
          }`}
          onClick={() => setView("explorer")}
        >
          Explorer
        </button>
      </nav>
      {view === "dashboard" ? <CodeViewDashboard /> : <ArchaeologyExplorer />}
    </div>
  );
}

export default App;
