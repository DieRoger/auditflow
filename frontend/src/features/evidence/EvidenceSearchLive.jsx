/** EvidenceSearchLive — 真实 API 证据检索 (Knowledge Search) */
import React from "react";
import api from "../../services/api.js";

function EvidenceSearchLive() {
  var [query, setQuery] = React.useState("Revenue recognition risk");
  var [results, setResults] = React.useState([]);
  var [error, setError] = React.useState("");
  var [loading, setLoading] = React.useState(false);

  function search() {
    setLoading(true);
    setError("");
    api.searchKnowledge(query, 5)
      .then(function (data) {
        var hits = data && (data.results || data.hits || []);
        setResults(Array.isArray(hits) ? hits : []);
      })
      .catch(function (e) { setError(e.message); setResults([]); })
      .finally(function () { setLoading(false); });
  }

  return React.createElement("div", null,
    React.createElement("h2", { style: { margin: "0 0 16px", fontSize: 18 } }, "Evidence Search — Live API"),

    React.createElement("div", { style: { display: "flex", gap: 8, marginBottom: 16 } },
      React.createElement("input", {
        value: query,
        onChange: function (e) { setQuery(e.target.value); },
        onKeyDown: function (e) { if (e.key === "Enter") search(); },
        placeholder: "Search audit standards / evidence...",
        style: { flex: 1, padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 13 },
      }),
      React.createElement("button", {
        onClick: search, disabled: loading,
        style: { padding: "8px 16px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 },
      }, loading ? "Searching..." : "Search"),
    ),

    error ? React.createElement("div", { style: { color: "#dc2626", fontSize: 13, marginBottom: 12 } }, error) : null,

    results.length === 0 && !error && !loading
      ? React.createElement("div", { style: { color: "#94a3b8", fontSize: 13 } }, "No results. Start the backend with PGVector + documents indexed.")
      : results.map(function (r, i) {
          var content = r.content || r.excerpt || r.text || "";
          return React.createElement("div", {
            key: i,
            style: { background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: 12, marginBottom: 8 },
          },
            React.createElement("div", { style: { fontSize: 12, color: "#64748b", marginBottom: 4 } },
              "doc=" + (r.document_id || "?") + " page=" + (r.page || "?") + " score=" + (r.score !== undefined ? r.score.toFixed(3) : "?")),
            React.createElement("div", { style: { fontSize: 13, lineHeight: 1.5 } }, String(content).slice(0, 300)),
          );
        }),
  );
}

export default EvidenceSearchLive;
