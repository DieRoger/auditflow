/** WorkflowTraceLive — 真实 API 执行轨迹 (Workflow Trace) */
import React from "react";
import api from "../../services/api.js";

function WorkflowTraceLive() {
  var [workflowId, setWorkflowId] = React.useState("");
  var [traces, setTraces] = React.useState([]);
  var [error, setError] = React.useState("");

  function load() {
    if (!workflowId.trim()) { setError("Enter a workflow ID"); return; }
    setError("");
    api.getWorkflowTrace(workflowId.trim())
      .then(function (data) {
        var t = data && (data.traces || data.trace || []);
        setTraces(Array.isArray(t) ? t : []);
      })
      .catch(function (e) { setError(e.message); setTraces([]); });
  }

  return React.createElement("div", null,
    React.createElement("h2", { style: { margin: "0 0 16px", fontSize: 18 } }, "Workflow Trace — Live API"),

    React.createElement("div", { style: { display: "flex", gap: 8, marginBottom: 16 } },
      React.createElement("input", {
        value: workflowId,
        onChange: function (e) { setWorkflowId(e.target.value); },
        placeholder: "workflow_id (e.g. 4a9f...)",
        style: { flex: 1, padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 13 },
      }),
      React.createElement("button", {
        onClick: load,
        style: { padding: "8px 16px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 },
      }, "Load Trace"),
    ),

    error ? React.createElement("div", { style: { color: "#dc2626", fontSize: 13, marginBottom: 12 } }, error) : null,

    traces.length === 0 && !error
      ? React.createElement("div", { style: { color: "#94a3b8", fontSize: 13 } }, "No traces. Create & run a workflow first.")
      : React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 13 } },
          React.createElement("thead", null,
            React.createElement("tr", null,
              ["#", "Event", "Agent", "Duration", "Status"].map(function (h) {
                return React.createElement("th", { key: h, style: { textAlign: "left", padding: "8px", borderBottom: "2px solid #e2e8f0", color: "#64748b", fontWeight: 600 } }, h);
              }),
            ),
          ),
          React.createElement("tbody", null,
            traces.map(function (t, i) {
              return React.createElement("tr", { key: i },
                React.createElement("td", { style: { padding: "8px", borderBottom: "1px solid #f1f5f9", color: "#94a3b8" } }, i + 1),
                React.createElement("td", { style: { padding: "8px", borderBottom: "1px solid #f1f5f9" } }, t.event_type || t.step || "?"),
                React.createElement("td", { style: { padding: "8px", borderBottom: "1px solid #f1f5f9" } }, t.agent_name || "-"),
                React.createElement("td", { style: { padding: "8px", borderBottom: "1px solid #f1f5f9" } }, (t.duration_ms || 0) + "ms"),
                React.createElement("td", { style: { padding: "8px", borderBottom: "1px solid #f1f5f9" } }, t.error ? "ERROR" : "OK"),
              );
            }),
          ),
        ),
  );
}

export default WorkflowTraceLive;
