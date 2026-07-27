import React, { useState } from "react";

interface ApprovalItem {
  id: string;
  agentName: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  summary: string;
}

const SEVERITY_CONFIG: Record<string, { color: string; bg: string }> = {
  HIGH: { color: "#fff", bg: "#dc2626" },
  MEDIUM: { color: "#1e293b", bg: "#eab308" },
  LOW: { color: "#fff", bg: "#16a34a" },
};

const MOCK_ITEMS: ApprovalItem[] = [
  { id: "a1", agentName: "Planner", severity: "HIGH", summary: "Audit scope identifies a material misstatement risk in revenue recognition requiring additional substantive testing." },
  { id: "a2", agentName: "Risk Agent", severity: "MEDIUM", summary: "Control deficiency detected in procurement approval workflow — compensating controls exist but need verification." },
  { id: "a3", agentName: "Evidence Agent", severity: "LOW", summary: "Supporting invoice for journal entry #1045 was located and cross-referenced successfully." },
  { id: "a4", agentName: "Reviewer", severity: "HIGH", summary: "Prior-period adjustment in goodwill impairment model uses unsubstantiated discount rate assumptions." },
  { id: "a5", agentName: "Knowledge Agent", severity: "MEDIUM", summary: "Regulatory citation SAS-145 may apply to the new lease accounting treatment under ASC 842." },
];

const ApprovalPanel: React.FC = () => {
  const [items, setItems] = useState<ApprovalItem[]>(MOCK_ITEMS);

  const handleAction = (id: string, action: "approved" | "rejected") => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif", maxWidth: 720 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0, marginBottom: 4 }}>Pending Approvals</h1>
      <p style={{ fontSize: 13, color: "#64748b", margin: 0, marginBottom: 20 }}>
        {items.length} item{items.length !== 1 ? "s" : ""} awaiting review
      </p>
      {items.length === 0 && (
        <div style={{ textAlign: "center", padding: 48, color: "#94a3b8", fontSize: 14 }}>
          No pending approvals. All items have been reviewed.
        </div>
      )}
      {items.map((item) => {
        const sev = SEVERITY_CONFIG[item.severity];
        return (
          <div
            key={item.id}
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: 10,
              padding: 16,
              marginBottom: 12,
              background: "#fff",
              boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 14, color: "#0f172a" }}>{item.agentName}</span>
              <span
                style={{
                  display: "inline-block",
                  fontSize: 11,
                  fontWeight: 600,
                  lineHeight: "18px",
                  padding: "0 8px",
                  borderRadius: 10,
                  color: sev.color,
                  background: sev.bg,
                }}
              >
                {item.severity}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: 13, color: "#334155", lineHeight: 1.5, marginBottom: 12 }}>
              {item.summary}
            </p>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => handleAction(item.id, "approved")}
                style={{
                  padding: "6px 16px",
                  fontSize: 13,
                  fontWeight: 500,
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  color: "#fff",
                  background: "#16a34a",
                }}
              >
                Approve
              </button>
              <button
                onClick={() => handleAction(item.id, "rejected")}
                style={{
                  padding: "6px 16px",
                  fontSize: 13,
                  fontWeight: 500,
                  border: "1px solid #e2e8f0",
                  borderRadius: 6,
                  cursor: "pointer",
                  color: "#dc2626",
                  background: "#fff",
                }}
              >
                Reject
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ApprovalPanel;
