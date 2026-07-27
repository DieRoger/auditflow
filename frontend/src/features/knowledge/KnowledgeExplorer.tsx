import React, { useState, useEffect } from "react";

interface ReasoningChain {
  area: string;
  risk: string;
  assertions: string[];
  procedures: { type: string; evidence_required: string[] }[];
  related_standards: string[];
}

const seedData: ReasoningChain[] = [
  { area: "revenue_recognition", risk: "Aggressive Revenue Recognition", assertions: ["Existence", "Accuracy", "Cutoff"],
    procedures: [{ type: "Inspection", evidence_required: ["sales_contracts", "shipping_docs"] }, { type: "Confirmation", evidence_required: ["customer_confirmations"] }],
    related_standards: ["IFRS 15.27", "ISA 240.32", "ISA 500.6"] },
  { area: "receivable_impairment", risk: "Inadequate Bad Debt Provision", assertions: ["Valuation", "Completeness"],
    procedures: [{ type: "Analytical", evidence_required: ["aging_report", "ar_ledger"] }, { type: "Confirmation", evidence_required: ["customer_confirmations"] }],
    related_standards: ["IAS 36.59", "ISA 330.18"] },
  { area: "inventory_valuation", risk: "Inventory Obsolescence Risk", assertions: ["Valuation", "Existence"],
    procedures: [{ type: "Inspection", evidence_required: ["inventory_list", "slow_moving_report"] }, { type: "Recalculation", evidence_required: ["costing_sheets"] }],
    related_standards: ["IAS 2.9", "ISA 501.4"] },
  { area: "expense_cutoff", risk: "Expense Capitalization Error", assertions: ["Cutoff", "Accuracy"],
    procedures: [{ type: "Inspection", evidence_required: ["invoices", "general_ledger"] }, { type: "Analytical", evidence_required: ["expense_summary"] }],
    related_standards: ["IAS 1.27", "ISA 500.8"] },
  { area: "fraud_risk", risk: "Management Override", assertions: ["Existence", "Accuracy"],
    procedures: [{ type: "Inspection", evidence_required: ["journal_entry_log", "accounting_estimates"] }, { type: "Analytical", evidence_required: ["revenue_analysis"] }],
    related_standards: ["ISA 240.32", "ISA 240.46"] },
];

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

const KnowledgeExplorer: React.FC = () => {
  const [chains] = useState(seedData);
  const [selected, setSelected] = useState<ReasoningChain | null>(null);
  const [search, setSearch] = useState("");

  const filtered = chains.filter(c =>
    c.area.toLowerCase().includes(search.toLowerCase()) ||
    c.risk.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    if (!selected && filtered.length > 0) setSelected(filtered[0]);
  }, [search]);

  return (
    <div style={{ display: "flex", height: "calc(100vh - 48px)", fontFamily: "system-ui, sans-serif" }}>
      {/* 左侧列表 */}
      <div style={{ width: 320, borderRight: "1px solid #e2e8f0", padding: 16, overflowY: "auto" }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>Audit Ontology</h2>
        <input
          placeholder="Search areas..."
          value={search} onChange={(e) => setSearch(e.target.value)}
          style={{ width: "100%", padding: "6px 8px", marginBottom: 12, border: "1px solid #cbd5e1", borderRadius: 4 }}
        />
        {filtered.map((c) => (
          <div
            key={c.area}
            onClick={() => setSelected(c)}
            style={{
              padding: "8px 12px", marginBottom: 4, borderRadius: 6, cursor: "pointer",
              background: selected?.area === c.area ? "#eff6ff" : "transparent",
              borderLeft: selected?.area === c.area ? "3px solid #3b82f6" : "3px solid transparent",
            }}
          >
            <div style={{ fontWeight: 500, fontSize: 14 }}>{c.area.replace(/_/g, " ")}</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>{c.risk}</div>
          </div>
        ))}
      </div>

      {/* 右侧详情 */}
      <div style={{ flex: 1, padding: 24, overflowY: "auto" }}>
        {selected && (
          <>
            <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4, textTransform: "capitalize" }}>
              {selected.area.replace(/_/g, " ")}
            </h1>
            <div style={{ fontSize: 14, color: "#64748b", marginBottom: 24 }}>{selected.risk}</div>

            {/* 推理链可视化 */}
            <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
              {["AuditArea", "Risk", ...selected.assertions.map(a => `Assertion: ${a}`), ...selected.procedures.map(p => `Procedure: ${p.type}`)]
                .map((label, i) => (
                  <div key={label} style={{
                    padding: "6px 14px", borderRadius: 20, fontSize: 12, fontWeight: 500,
                    background: COLORS[i % COLORS.length] + "20",
                    color: COLORS[i % COLORS.length],
                    border: `1px solid ${COLORS[i % COLORS.length]}40`,
                  }}>
                    {label}
                  </div>
                ))}
            </div>

            {/* Assertions */}
            <Section title="Assertions Violated">
              {selected.assertions.map(a => <Chip key={a} label={a} />)}
            </Section>

            {/* Procedures */}
            <Section title="Audit Procedures">
              {selected.procedures.map((p, i) => (
                <div key={i} style={{ marginBottom: 8, padding: "8px 12px", background: "#f8fafc", borderRadius: 6 }}>
                  <strong>{p.type}</strong>
                  <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                    Evidence: {p.evidence_required.join(", ")}
                  </div>
                </div>
              ))}
            </Section>

            {/* Standards */}
            <Section title="Related Standards">
              {selected.related_standards.map(s => <Chip key={s} label={s} color="#8b5cf6" />)}
            </Section>
          </>
        )}
      </div>
    </div>
  );
};

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ marginBottom: 20 }}>
    <h3 style={{ fontSize: 14, fontWeight: 600, color: "#475569", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>
      {title}
    </h3>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{children}</div>
  </div>
);

const Chip: React.FC<{ label: string; color?: string }> = ({ label, color = "#3b82f6" }) => (
  <span style={{
    padding: "4px 10px", borderRadius: 12, fontSize: 12, fontWeight: 500,
    background: color + "15", color, border: `1px solid ${color}30`,
  }}>
    {label}
  </span>
);

export default KnowledgeExplorer;
