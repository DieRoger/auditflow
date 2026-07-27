import React, { useState } from "react";

interface EvidenceItem {
  id: string;
  claim: string;
  source: string;
  excerpt: string;
  confidence: number;
  verified: boolean;
}

const mockEvidence: EvidenceItem[] = [
  { id: "ev_001", claim: "Revenue increased 45%", source: "Annual_Report_2025.pdf (p.32)", excerpt: "Revenue 2025: $145M, 2024: $100M — YoY increase of 45%", confidence: 0.99, verified: true },
  { id: "ev_002", claim: "Receivable days increased to 120", source: "AR_Aging.xlsx (Sheet: Summary)", excerpt: "AR Turnover Days: 120 (prior year: 90)", confidence: 0.97, verified: true },
  { id: "ev_003", claim: "Industry average growth is 10%", source: "Industry_Report_2025.pdf (p.8)", excerpt: "Median revenue growth for manufacturing sector: 8-12%", confidence: 0.85, verified: true },
  { id: "ev_004", claim: "Inventory obsolescence risk exists", source: "Inventory_Report.xlsx", excerpt: "Slow-moving items: SKU-1012, SKU-2034 — aged > 12 months", confidence: 0.72, verified: false },
];

const RISK_COLORS = ["#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6"];

const EvidenceBrowser: React.FC = () => {
  const [selected, setSelected] = useState<EvidenceItem | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const filtered = mockEvidence.filter(e => filter === "all" || (filter === "verified" && e.verified) || (filter === "unverified" && !e.verified));

  return (
    <div style={{ display: "flex", height: "calc(100vh - 48px)", fontFamily: "system-ui, sans-serif" }}>
      {/* 左侧 Evidence 列表 */}
      <div style={{ width: 380, borderRight: "1px solid #e2e8f0", padding: 16, overflowY: "auto" }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>Evidence Explorer</h2>

        <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
          {["all", "verified", "unverified"].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 500, cursor: "pointer", border: "1px solid #cbd5e1",
              background: filter === f ? "#3b82f6" : "#fff", color: filter === f ? "#fff" : "#475569",
            }}>{f}</button>
          ))}
        </div>

        <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>{filtered.length} items</div>

        {filtered.map((ev) => (
          <div key={ev.id} onClick={() => setSelected(ev)} style={{
            padding: "10px 12px", marginBottom: 6, borderRadius: 8, cursor: "pointer",
            background: selected?.id === ev.id ? "#eff6ff" : "#f8fafc",
            border: selected?.id === ev.id ? "1px solid #93c5fd" : "1px solid #e2e8f0",
          }}>
            <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>{ev.claim}</div>
            <div style={{ fontSize: 11, color: "#64748b" }}>{ev.source}</div>
            <div style={{ marginTop: 4, display: "flex", gap: 6 }}>
              <span style={{ fontSize: 11, padding: "1px 6px", borderRadius: 8, background: ev.verified ? "#dcfce7" : "#fef3c7", color: ev.verified ? "#16a34a" : "#d97706" }}>
                {ev.verified ? "Verified" : "Unverified"}
              </span>
              <span style={{ fontSize: 11, color: "#64748b" }}>{(ev.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* 右侧详情面板 */}
      <div style={{ flex: 1, padding: 24, overflowY: "auto" }}>
        {selected ? (
          <>
            <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>{selected.claim}</h1>

            <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
              <InfoCard label="Source" value={selected.source} />
              <InfoCard label="Confidence" value={`${(selected.confidence * 100).toFixed(0)}%`} />
              <InfoCard label="Status" value={selected.verified ? "Verified" : "Unverified"} color={selected.verified ? "#16a34a" : "#d97706"} />
            </div>

            <Section title="Source Excerpt">
              <div style={{ background: "#f8fafc", padding: 16, borderRadius: 8, fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                {selected.excerpt}
              </div>
            </Section>

            <Section title="Citation Chain">
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                <Node label="Claim" color="#3b82f6" />
                <Arrow />
                <Node label="Evidence" color="#10b981" />
                <Arrow />
                <Node label={selected.source.split("(")[0].trim()} color="#8b5cf6" />
              </div>
            </Section>
          </>
        ) : (
          <div style={{ textAlign: "center", padding: 80, color: "#94a3b8" }}>Select an evidence item to view details</div>
        )}
      </div>
    </div>
  );
};

const InfoCard: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <div style={{ padding: "10px 14px", background: "#f8fafc", borderRadius: 8, flex: 1 }}>
    <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 2 }}>{label}</div>
    <div style={{ fontSize: 14, fontWeight: 500, color: color || "#1e293b" }}>{value}</div>
  </div>
);

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ marginBottom: 20 }}>
    <h3 style={{ fontSize: 13, fontWeight: 600, color: "#475569", marginBottom: 8 }}>{title}</h3>
    {children}
  </div>
);

const Node: React.FC<{ label: string; color: string }> = ({ label, color }) => (
  <span style={{ padding: "4px 10px", borderRadius: 12, fontSize: 12, fontWeight: 500, background: color + "15", color, border: `1px solid ${color}30` }}>{label}</span>
);

const Arrow: React.FC = () => <span style={{ color: "#94a3b8", fontSize: 16 }}>→</span>;

export default EvidenceBrowser;
