import React from "react";

/* Agent Trace Viewer — 显示 Agent 执行轨迹 */

var sampleTraces = [
  { agent: "Planner", status: "completed", duration: "3.7s", tokens: 401, step: 1 },
  { agent: "Knowledge", status: "completed", duration: "11.4s", tokens: 1111, step: 2 },
  { agent: "Risk", status: "completed", duration: "5.2s", tokens: 763, step: 3,
    output: "Revenue Recognition Risk [HIGH]" },
  { agent: "Evidence", status: "completed", duration: "1.9s", tokens: 288, step: 4,
    output: "Coverage: 2/3 claims matched" },
  { agent: "Reviewer", status: "completed", duration: "3.1s", tokens: 438, step: 5,
    output: "Quality Score: 60%, Hallucination: 40%" },
];

function AgentTraceViewer() {
  return React.createElement("div", { style: { padding: 16, fontFamily: "system-ui" } },
    React.createElement("h2", { style: { fontSize: 18, marginBottom: 16 } }, "Agent Execution Trace"),

    // Timeline header
    React.createElement("div", { style: { display: "flex", gap: 0, marginBottom: 16 } },
      sampleTraces.map(function(t, i) {
        return React.createElement("div", {
          key: i,
          style: {
            flex: 1, textAlign: "center", padding: "8px 4px",
            background: t.status === "completed" ? "#22c55e" : "#94a3b8",
            color: "#fff", fontSize: 11, fontWeight: 600,
            borderRadius: i === 0 ? "4px 0 0 4px" : i === sampleTraces.length - 1 ? "0 4px 4px 0" : "0",
          }
        }, t.agent);
      })
    ),

    // Trace table
    React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 13 } },
      React.createElement("thead", null,
        React.createElement("tr", { style: { background: "#f8fafc", textAlign: "left" } },
          React.createElement("th", { style: thStyle }, "Step"),
          React.createElement("th", { style: thStyle }, "Agent"),
          React.createElement("th", { style: thStyle }, "Status"),
          React.createElement("th", { style: thStyle }, "Duration"),
          React.createElement("th", { style: thStyle }, "Tokens"),
          React.createElement("th", { style: thStyle }, "Output"),
        )
      ),
      React.createElement("tbody", null,
        sampleTraces.map(function(t, i) {
          return React.createElement("tr", { key: i, style: { borderBottom: "1px solid #e2e8f0" } },
            React.createElement("td", { style: tdStyle }, t.step),
            React.createElement("td", { style: { ...tdStyle, fontWeight: 600 } }, t.agent),
            React.createElement("td", { style: tdStyle },
              React.createElement("span", {
                style: {
                  background: t.status === "completed" ? "#dcfce7" : "#fef3c7",
                  color: t.status === "completed" ? "#16a34a" : "#d97706",
                  borderRadius: 12, padding: "2px 8px", fontSize: 11,
                }
              }, t.status)
            ),
            React.createElement("td", { style: tdStyle }, t.duration),
            React.createElement("td", { style: tdStyle }, t.tokens),
            React.createElement("td", { style: { ...tdStyle, color: "#64748b", fontSize: 12 } },
              t.output || "-"),
          );
        })
      )
    )
  );
}

var thStyle = { padding: "8px 12px", fontWeight: 600, fontSize: 12, color: "#475569" };
var tdStyle = { padding: "8px 12px", fontSize: 13 };

export default AgentTraceViewer;
