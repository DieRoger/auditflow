import React from "react";

/* Evidence Graph — React Flow visualization of evidence chain
   Simplified version using HTML/CSS (no JSX, no TS) */

function EvidenceGraph() {
  return React.createElement("div", { style: { padding: 16, fontFamily: "system-ui" } },
    React.createElement("h2", { style: { fontSize: 18, marginBottom: 16 } }, "Evidence Chain"),

    // Simple node visualization (CSS-based, no React Flow dependency needed)
    React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 0, alignItems: "center" } },

      // Risk node
      React.createElement("div", { style: riskNodeStyle },
        React.createElement("div", { style: { fontWeight: 600, fontSize: 13 } }, "Revenue Recognition Risk"),
        React.createElement("div", { style: { fontSize: 11, color: "#dc2626", marginTop: 4 } }, "HIGH Severity")
      ),
      React.createElement("div", { style: arrowStyle }, "\u2193"),

      // Evidence node
      React.createElement("div", { style: evidenceNodeStyle },
        React.createElement("div", { style: { fontWeight: 600, fontSize: 13 } }, "Contract Analysis"),
        React.createElement("div", { style: { fontSize: 11, color: "#64748b", marginTop: 4 } }, "3 deals in final week")
      ),
      React.createElement("div", { style: arrowStyle }, "\u2193"),

      // Citation node
      React.createElement("div", { style: citationNodeStyle },
        React.createElement("div", { style: { fontWeight: 600, fontSize: 13 } }, "Source Document"),
        React.createElement("div", { style: { fontSize: 11, color: "#64748b", marginTop: 4 } }, "AnnualReport.pdf  p.32"),
      ),
      React.createElement("div", { style: arrowStyle }, "\u2193"),

      // Procedure node
      React.createElement("div", { style: { ...evidenceNodeStyle, borderColor: "#8b5cf6", background: "#f5f3ff" } },
        React.createElement("div", { style: { fontWeight: 600, fontSize: 13 } }, "Audit Procedure"),
        React.createElement("div", { style: { fontSize: 11, color: "#64748b", marginTop: 4 } }, "Substantive testing recommended")
      ),
    )
  );
}

var riskNodeStyle = {
  border: "2px solid #dc2626",
  borderRadius: 8,
  padding: "12px 20px",
  background: "#fef2f2",
  minWidth: 200,
  textAlign: "center",
};

var evidenceNodeStyle = {
  border: "2px solid #3b82f6",
  borderRadius: 8,
  padding: "12px 20px",
  background: "#eff6ff",
  minWidth: 200,
  textAlign: "center",
};

var citationNodeStyle = {
  border: "2px solid #22c55e",
  borderRadius: 8,
  padding: "12px 20px",
  background: "#f0fdf4",
  minWidth: 200,
  textAlign: "center",
};

var arrowStyle = {
  fontSize: 24,
  color: "#94a3b8",
  padding: "4px 0",
};

export default EvidenceGraph;
