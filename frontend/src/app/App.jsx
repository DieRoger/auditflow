import React from "react";

function App() {
  return React.createElement("div", { style: { padding: 40, fontFamily: "system-ui, sans-serif" } },
    React.createElement("h1", { style: { fontSize: 28, marginBottom: 8 } }, "AuditFlow"),
    React.createElement("p", { style: { color: "#64748b", marginBottom: 24 } }, "AI-Native Audit Intelligence Platform"),
    React.createElement("div", { style: { display: "flex", gap: 16 } },
      React.createElement("div", { style: { flex: 1, background: "#f8fafc", borderRadius: 8, padding: 16 } },
        React.createElement("h3", null, "Document Center"),
        React.createElement("p", { style: { color: "#94a3b8", fontSize: 13 } }, "Upload and manage audit documents")
      ),
      React.createElement("div", { style: { flex: 1, background: "#f8fafc", borderRadius: 8, padding: 16 } },
        React.createElement("h3", null, "Workflow Monitor"),
        React.createElement("p", { style: { color: "#94a3b8", fontSize: 13 } }, "Track audit pipeline progress")
      ),
      React.createElement("div", { style: { flex: 1, background: "#f8fafc", borderRadius: 8, padding: 16 } },
        React.createElement("h3", null, "Risk Matrix"),
        React.createElement("p", { style: { color: "#94a3b8", fontSize: 13 } }, "View identified audit risks")
      )
    )
  );
}

export default App;
