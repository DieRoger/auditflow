import React from "react";
import AgentTraceViewer from "../features/workflow/AgentTraceViewer.jsx";
import EvidenceGraph from "../features/evidence/EvidenceGraph.jsx";
import DashboardLive from "../features/dashboard/DashboardLive.jsx";
import WorkflowTraceLive from "../features/workflow/WorkflowTraceLive.jsx";
import EvidenceSearchLive from "../features/evidence/EvidenceSearchLive.jsx";

var pages = [
  { id: "dashboard", label: "Dashboard", desc: "Audit overview and KPIs" },
  { id: "dashboard-live", label: "Dashboard (Live)", desc: "Real API — agents / workflows / documents", component: "dashboard-live" },
  { id: "documents", label: "Document Center", desc: "Upload and manage audit documents" },
  { id: "workflow", label: "Workflow Monitor", desc: "Track audit pipeline progress" },
  { id: "trace", label: "Agent Trace", desc: "View agent execution timeline", component: "trace" },
  { id: "trace-live", label: "Trace (Live)", desc: "Real API — workflow execution trace", component: "trace-live" },
  { id: "evidence", label: "Evidence Graph", desc: "Evidence chain visualization", component: "evidence" },
  { id: "evidence-live", label: "Evidence Search (Live)", desc: "Real API — knowledge retrieval", component: "evidence-live" },
  { id: "risks", label: "Risk Matrix", desc: "View identified audit risks" },
  { id: "approvals", label: "Approvals", desc: "Pending human reviews" },
];

function App() {
  var [activePage, setActivePage] = React.useState(null);

  return React.createElement("div", { style: { fontFamily: "system-ui, sans-serif" } },

    // Header
    React.createElement("div", { style: { background: "#1e293b", color: "#fff", padding: "16px 24px" } },
      React.createElement("h1", { style: { fontSize: 20, margin: 0 } }, "AuditFlow"),
      React.createElement("p", { style: { margin: "4px 0 0", fontSize: 13, color: "#94a3b8" } },
        "AI-Native Audit Intelligence Platform"),
    ),

    // Navigation tabs
    React.createElement("div", { style: { display: "flex", gap: 0, borderBottom: "1px solid #e2e8f0", background: "#f8fafc" } },
      pages.map(function(p) {
        var isActive = activePage === p.id;
        return React.createElement("button", {
          key: p.id,
          onClick: function() { setActivePage(p.id); },
          style: {
            padding: "10px 16px", border: "none", cursor: "pointer",
            background: isActive ? "#fff" : "transparent",
            borderBottom: isActive ? "2px solid #3b82f6" : "2px solid transparent",
            fontWeight: isActive ? 600 : 400,
            fontSize: 13, color: isActive ? "#1e293b" : "#64748b",
          }
        }, p.label);
      })
    ),

    // Content area
    React.createElement("div", { style: { padding: 24 } },
      activePage === "trace"
        ? React.createElement(AgentTraceViewer, null)
        : activePage === "evidence"
        ? React.createElement(EvidenceGraph, null)
        : activePage === "dashboard-live"
        ? React.createElement(DashboardLive, null)
        : activePage === "trace-live"
        ? React.createElement(WorkflowTraceLive, null)
        : activePage === "evidence-live"
        ? React.createElement(EvidenceSearchLive, null)
        : React.createElement("div", { style: { display: "flex", gap: 16, flexWrap: "wrap" } },
            pages.map(function(p) {
              var isActive = activePage === p.id || (!activePage && p.id === "dashboard");
              return React.createElement("div", {
                key: p.id,
                onClick: function() { setActivePage(p.id); },
                style: {
                  flex: "1 1 280px", background: "#f8fafc", borderRadius: 8, padding: 20,
                  cursor: "pointer", border: isActive ? "2px solid #3b82f6" : "2px solid transparent",
                }
              },
                React.createElement("h3", { style: { margin: "0 0 4px", fontSize: 15 } }, p.label),
                React.createElement("p", { style: { margin: 0, color: "#94a3b8", fontSize: 13 } }, p.desc),
              );
            })
          )
    ),

    // Footer
    React.createElement("div", { style: { borderTop: "1px solid #e2e8f0", padding: "12px 24px", fontSize: 12, color: "#94a3b8" } },
      "AuditFlow v0.1.0 \u2014 AI-Native Audit Intelligence Platform"),
  );
}

export default App;
