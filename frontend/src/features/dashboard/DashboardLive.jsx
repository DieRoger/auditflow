/** DashboardLive — 真实 API 数据面板 (Agents / Workflows / Documents) */
import React from "react";
import api from "../../services/api.js";

function DashboardLive() {
  var [agents, setAgents] = React.useState([]);
  var [workflow, setWorkflow] = React.useState(null);
  var [docs, setDocs] = React.useState([]);
  var [error, setError] = React.useState("");
  var [loading, setLoading] = React.useState(false);

  React.useEffect(function () {
    api.listAgents()
      .then(function (a) { setAgents(a || []); })
      .catch(function (e) { setError("agents: " + e.message); });
    api.listDocuments()
      .then(function (d) { setDocs((d && d.documents) || []); })
      .catch(function (e) { /* documents may need MinIO — non-fatal */ });
  }, []);

  function createAndStart() {
    setLoading(true);
    setError("");
    api.createWorkflow({})
      .then(function (wf) {
        setWorkflow(wf);
        return api.startWorkflow(wf.workflow_id);
      })
      .then(function (running) { setWorkflow(running); })
      .catch(function (e) { setError("workflow: " + e.message); })
      .finally(function () { setLoading(false); });
  }

  function refresh() {
    if (!workflow) return;
    api.getWorkflow(workflow.workflow_id)
      .then(function (w) { setWorkflow(w); })
      .catch(function (e) { setError(e.message); });
  }

  return React.createElement("div", null,
    React.createElement("h2", { style: { margin: "0 0 16px", fontSize: 18 } }, "Dashboard — Live API"),

    // Workflow action bar
    React.createElement("div", { style: { display: "flex", gap: 8, marginBottom: 16 } },
      React.createElement("button", {
        onClick: createAndStart, disabled: loading,
        style: { padding: "8px 16px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 },
      }, loading ? "Starting..." : "Create & Start Workflow"),
      React.createElement("button", {
        onClick: refresh,
        style: { padding: "8px 16px", background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 6, cursor: "pointer", fontSize: 13 },
      }, "Refresh"),
    ),

    // Workflow status
    workflow
      ? React.createElement("div", { style: { background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: 12, marginBottom: 16 } },
          React.createElement("strong", null, "Workflow: ", workflow.workflow_id),
          React.createElement("span", { style: { marginLeft: 12, color: "#16a34a" } }, "Status: " + (workflow.status || "created")),
        )
      : null,

    // Error
    error ? React.createElement("div", { style: { color: "#dc2626", fontSize: 13, marginBottom: 12 } }, error) : null,

    // Agents grid
    React.createElement("h3", { style: { fontSize: 14, margin: "16px 0 8px" } }, "Registered Agents (" + agents.length + ")"),
    React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 8 } },
      agents.map(function (a) {
        return React.createElement("span", {
          key: a,
          style: { background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 20, padding: "4px 12px", fontSize: 12 },
        }, a);
      }),
    ),

    // Documents count
    React.createElement("h3", { style: { fontSize: 14, margin: "16px 0 8px" } }, "Documents (" + docs.length + ")"),
    React.createElement("div", { style: { fontSize: 12, color: "#64748b" } },
      docs.length > 0
        ? docs.map(function (d, i) { return React.createElement("div", { key: i }, "• " + (d.filename || d.document_id)); })
        : "No documents (MinIO required)",
    ),
  );
}

export default DashboardLive;
