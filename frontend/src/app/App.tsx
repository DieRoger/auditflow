import React from "react";

const App: React.FC = () => {
  return (
    <div style={{ padding: 40, fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: 28, marginBottom: 8 }}>AuditFlow</h1>
      <p style={{ color: "#64748b", marginBottom: 24 }}>AI-Native Audit Intelligence Platform</p>
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1, background: "#f8fafc", borderRadius: 8, padding: 16 }}>
          <h3>Document Center</h3>
          <p style={{ color: "#94a3b8", fontSize: 13 }}>Upload and manage audit documents</p>
        </div>
        <div style={{ flex: 1, background: "#f8fafc", borderRadius: 8, padding: 16 }}>
          <h3>Workflow Monitor</h3>
          <p style={{ color: "#94a3b8", fontSize: 13 }}>Track audit pipeline progress</p>
        </div>
        <div style={{ flex: 1, background: "#f8fafc", borderRadius: 8, padding: 16 }}>
          <h3>Risk Matrix</h3>
          <p style={{ color: "#94a3b8", fontSize: 13 }}>View identified audit risks</p>
        </div>
      </div>
    </div>
  );
};

export default App;
