import React, { useState } from "react";

type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

interface RiskItem {
  id: string;
  title: string;
  area: string;
  severity: Severity;
  probability: number;
  impact: string;
  relatedStandards: string[];
  description: string;
}

const mockRisks: RiskItem[] = [
  {
    id: "risk_001",
    title: "Revenue Overstatement - Channel Stuffing",
    area: "Revenue",
    severity: "CRITICAL",
    probability: 78,
    impact: "Material misstatement of $8.2M in Q4 revenue",
    relatedStandards: ["IFRS 15", "ISA 240"],
    description: "Indicators of channel stuffing through year-end incentives to distributors.",
  },
  {
    id: "risk_002",
    title: "Inventory Obsolescence Not Recognised",
    area: "Inventory",
    severity: "CRITICAL",
    probability: 65,
    impact: "Overstated inventory by ~$4.7M",
    relatedStandards: ["IAS 2", "ISA 501"],
    description: "Slow-moving SKUs aged >12 months without adequate NRV write-down.",
  },
  {
    id: "risk_003",
    title: "Unrecorded Liabilities - Side Agreements",
    area: "Revenue",
    severity: "HIGH",
    probability: 55,
    impact: "Potential off-balance sheet commitments up to $2.1M",
    relatedStandards: ["IFRS 15", "IFRS 9", "ISA 240"],
    description: "Possible side letters granting customers undisclosed rebate rights.",
  },
  {
    id: "risk_004",
    title: "AR ECL Model Understatement",
    area: "AR",
    severity: "HIGH",
    probability: 62,
    impact: "Allowance shortfall of $0.8M - $1.2M",
    relatedStandards: ["IFRS 9", "ISA 540"],
    description: "Forward-looking assumptions in ECL model not reflecting current economic downturn.",
  },
  {
    id: "risk_005",
    title: "Revenue Cut-Off Misstatement",
    area: "Revenue",
    severity: "MEDIUM",
    probability: 45,
    impact: "Timing misstatement affecting both FY2025 and FY2026",
    relatedStandards: ["IFRS 15", "ISA 330"],
    description: "Goods shipped near year-end may be recorded in incorrect period.",
  },
  {
    id: "risk_006",
    title: "Inventory Count Discrepancies",
    area: "Inventory",
    severity: "MEDIUM",
    probability: 40,
    impact: "Adjustment of ~$0.5M post-physical count",
    relatedStandards: ["IAS 2", "ISA 501"],
    description: "Cycle count variances observed at two warehouses in prior quarter.",
  },
  {
    id: "risk_007",
    title: "AR Ageing Data Integrity",
    area: "AR",
    severity: "LOW",
    probability: 30,
    impact: "Minor misstatement of aged bucket classification",
    relatedStandards: ["IFRS 9", "ISA 315"],
    description: "Customer payments misapplied to invoices, impacting ageing accuracy.",
  },
  {
    id: "risk_008",
    title: "Revenue Rebate Accrual Estimation",
    area: "Revenue",
    severity: "LOW",
    probability: 25,
    impact: "Estimate variance of +/- $0.3M",
    relatedStandards: ["IFRS 15", "ISA 540"],
    description: "Volume-based rebate accrual relies on subjective year-end forecasts.",
  },
];

const SEVERITY_ORDER: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

const SEVERITY_CONFIG: Record<Severity, { bg: string; badgeBg: string; border: string; label: string }> = {
  CRITICAL: { bg: "#fef2f2", badgeBg: "#dc2626", border: "#fca5a5", label: "CRITICAL" },
  HIGH:    { bg: "#fff7ed", badgeBg: "#ea580c", border: "#fdba74", label: "HIGH" },
  MEDIUM:  { bg: "#fefce8", badgeBg: "#ca8a04", border: "#fde047", label: "MEDIUM" },
  LOW:     { bg: "#f0fdf4", badgeBg: "#16a34a", border: "#86efac", label: "LOW" },
};

const AREA_COLORS: Record<string, string> = {
  Revenue: "#3b82f6",
  Inventory: "#8b5cf6",
  AR: "#06b6d4",
};

const RiskMatrix: React.FC = () => {
  const [selectedRisk, setSelectedRisk] = useState<RiskItem | null>(null);
  const [areaFilter, setAreaFilter] = useState<string>("All");

  const areas = Array.from(new Set(mockRisks.map((r) => r.area)));
  const filteredRisks =
    areaFilter === "All"
      ? mockRisks
      : mockRisks.filter((r) => r.area === areaFilter);

  const grouped = SEVERITY_ORDER.reduce<Record<Severity, RiskItem[]>>((acc, sev) => {
    acc[sev] = filteredRisks.filter((r) => r.severity === sev);
    return acc;
  }, {} as Record<Severity, RiskItem[]>);

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>Risk Matrix</h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0 0" }}>
            {mockRisks.length} risks identified across {areas.length} areas
          </p>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          {["All", ...areas].map((a) => (
            <button
              key={a}
              onClick={() => setAreaFilter(a)}
              style={{
                padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 500,
                cursor: "pointer", border: "1px solid #cbd5e1",
                background: areaFilter === a ? "#3b82f6" : "#fff",
                color: areaFilter === a ? "#fff" : "#475569",
                transition: "background 0.15s",
              }}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      {/* Severity Groups */}
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {SEVERITY_ORDER.map((severity) => {
          const risks = grouped[severity];
          const cfg = SEVERITY_CONFIG[severity];
          if (risks.length === 0) return null;

          return (
            <div key={severity}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <div style={{
                  width: 10, height: 10, borderRadius: "50%",
                  background: cfg.badgeBg, flexShrink: 0,
                }} />
                <h2 style={{ fontSize: 14, fontWeight: 600, color: "#1e293b", margin: 0 }}>
                  {severity}
                </h2>
                <span style={{ fontSize: 12, color: "#94a3b8" }}>({risks.length})</span>
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                {risks.map((risk) => {
                  const areaColor = AREA_COLORS[risk.area] || "#64748b";
                  const isSelected = selectedRisk?.id === risk.id;

                  return (
                    <div
                      key={risk.id}
                      onClick={() => setSelectedRisk(isSelected ? null : risk)}
                      style={{
                        width: 300, padding: 14, borderRadius: 8, cursor: "pointer",
                        border: `1px solid ${isSelected ? cfg.border : "#e2e8f0"}`,
                        background: cfg.bg,
                        boxShadow: isSelected ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                        transition: "box-shadow 0.15s",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                        <h3 style={{ fontSize: 13, fontWeight: 600, color: "#1e293b", margin: 0, lineHeight: 1.3, maxWidth: 180 }}>
                          {risk.title}
                        </h3>
                        <span style={{
                          padding: "2px 8px", borderRadius: 8, fontSize: 10, fontWeight: 700,
                          background: cfg.badgeBg, color: "#fff", whiteSpace: "nowrap",
                        }}>
                          {cfg.label}
                        </span>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                        <span style={{
                          padding: "1px 8px", borderRadius: 8, fontSize: 11, fontWeight: 500,
                          background: areaColor + "18", color: areaColor,
                        }}>
                          {risk.area}
                        </span>
                        <span style={{ fontSize: 12, color: "#64748b" }}>
                          {risk.probability}% probability
                        </span>
                      </div>

                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {risk.relatedStandards.map((std) => (
                          <span key={std} style={{
                            fontSize: 10, padding: "1px 6px", borderRadius: 4,
                            background: "#f1f5f9", color: "#64748b",
                          }}>
                            {std}
                          </span>
                        ))}
                      </div>

                      {isSelected && (
                        <div style={{
                          marginTop: 10, paddingTop: 10, borderTop: "1px solid #e2e8f0",
                          fontSize: 12, lineHeight: 1.5, color: "#475569",
                        }}>
                          {risk.description}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Footer */}
      <div style={{
        marginTop: 28, padding: "12px 16px", borderRadius: 8,
        background: "#f8fafc", border: "1px solid #e2e8f0",
        fontSize: 12, color: "#64748b", lineHeight: 1.6,
      }}>
        <strong>Risk Heatmap Summary:</strong>{" "}
        {SEVERITY_ORDER.map((sev) => {
          const count = grouped[sev].length;
          if (count === 0) return null;
          const cfg = SEVERITY_CONFIG[sev];
          return (
            <span key={sev} style={{ marginRight: 12 }}>
              <span style={{ color: cfg.badgeBg, fontWeight: 600 }}>{sev}</span>: {count}
            </span>
          );
        })}
        <span style={{ marginLeft: 12, color: "#94a3b8" }}>
          Click any risk card to expand details.
        </span>
      </div>
    </div>
  );
};

export default RiskMatrix;
