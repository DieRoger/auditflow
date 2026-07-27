import React, { useState } from "react";

interface AuditReport {
  id: string;
  entityName: string;
  period: string;
  reportDate: string;
  opinion: string;
  opinionType: "Unmodified" | "Qualified" | "Adverse" | "Disclaimer";
  basisForOpinion: string;
  keyAuditMatters: { title: string; detail: string }[];
  responsibilities: { entity: string; auditor: string };
  emphasisOfMatter?: string;
}

const mockReport: AuditReport = {
  id: "rep_001",
  entityName: "ABC Manufacturing Co., Ltd.",
  period: "FY2025 (January 1, 2025 - December 31, 2025)",
  reportDate: "March 15, 2026",
  opinionType: "Unmodified",
  opinion:
    "In our opinion, the financial statements present fairly, in all material respects, " +
    "the financial position of ABC Manufacturing Co., Ltd. as at December 31, 2025, " +
    "and its financial performance and its cash flows for the year then ended in accordance " +
    "with International Financial Reporting Standards (IFRS).",
  basisForOpinion:
    "We conducted our audit in accordance with International Standards on Auditing (ISAs). " +
    "Our responsibilities under those standards are further described in the Auditor's " +
    "Responsibilities for the Audit of the Financial Statements section of our report. " +
    "We are independent of the entity in accordance with the International Ethics Standards " +
    "Board for Accountants' International Code of Ethics for Professional Accountants (IESBA Code), " +
    "and we have fulfilled our other ethical responsibilities in accordance with the IESBA Code. " +
    "We believe that the audit evidence we have obtained is sufficient and appropriate to provide " +
    "a basis for our opinion.",
  keyAuditMatters: [
    {
      title: "Revenue Recognition - Significant Judgement",
      detail:
        "Revenue of $145M includes significant estimates related to variable consideration " +
        "and customer rebates totaling approximately $8.2M. We tested controls over revenue " +
        "cut-off and performed substantive testing on a sample of sales transactions. " +
        "We assessed management's estimates against historical trends and contractual terms.",
    },
    {
      title: "Valuation of Inventory - Net Realisable Value",
      detail:
        "Inventory of $62M includes $4.7M in slow-moving items subject to NRV assessment. " +
        "We evaluated management's forecasts of future selling prices and costs to complete. " +
        "We also attended physical inventory counts at three major warehouses.",
    },
    {
      title: "Recoverability of Trade Receivables",
      detail:
        "Gross trade receivables of $38M with an allowance for expected credit losses of $1.5M. " +
        "We assessed the methodology used for ECL calculation, tested the ageing analysis, " +
        "and evaluated the forward-looking assumptions applied to loss rates.",
    },
  ],
  responsibilities: {
    entity:
      "Management is responsible for the preparation and fair presentation of the financial " +
      "statements in accordance with IFRS, and for such internal control as management " +
      "determines is necessary to enable the preparation of financial statements that are " +
      "free from material misstatement, whether due to fraud or error.",
    auditor:
      "Our objectives are to obtain reasonable assurance about whether the financial statements " +
      "as a whole are free from material misstatement, whether due to fraud or error, and to " +
      "issue an auditor's report that includes our opinion. Reasonable assurance is a high " +
      "level of assurance but is not a guarantee that an audit conducted in accordance with ISAs " +
      "will always detect a material misstatement when it exists.",
  },
  emphasisOfMatter:
    "We draw attention to Note 18 of the financial statements, which describes the ongoing " +
    "regulatory review of certain export tax incentives. Our opinion is not modified in respect of this matter.",
};

const OPINION_BADGE_COLORS: Record<string, { bg: string; text: string }> = {
  Unmodified: { bg: "#dcfce7", text: "#16a34a" },
  Qualified: { bg: "#fef3c7", text: "#d97706" },
  Adverse: { bg: "#fee2e2", text: "#dc2626" },
  Disclaimer: { bg: "#f1f5f9", text: "#64748b" },
};

const ReportViewer: React.FC = () => {
  const [report] = useState<AuditReport>(mockReport);
  const [activeSection, setActiveSection] = useState<string>("opinion");

  const badge = OPINION_BADGE_COLORS[report.opinionType];

  const sections: { id: string; label: string }[] = [
    { id: "opinion", label: "Audit Opinion" },
    { id: "basis", label: "Basis for Opinion" },
    { id: "kam", label: "Key Audit Matters" },
    { id: "responsibilities", label: "Responsibilities" },
  ];

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif", maxWidth: 960, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>Independent Auditor's Report</h1>
            <p style={{ fontSize: 14, color: "#475569", margin: "4px 0 0 0" }}>{report.entityName}</p>
          </div>
          <span style={{
            padding: "4px 12px", borderRadius: 12, fontSize: 12, fontWeight: 600,
            background: badge.bg, color: badge.text, whiteSpace: "nowrap",
          }}>
            {report.opinionType} Opinion
          </span>
        </div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>
          Period: {report.period} &middot; Report Date: {report.reportDate}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #e2e8f0", marginBottom: 20 }}>
        {sections.map((sec) => (
          <button
            key={sec.id}
            onClick={() => setActiveSection(sec.id)}
            style={{
              padding: "8px 16px", fontSize: 13, fontWeight: 500, cursor: "pointer",
              border: "none", borderBottom: activeSection === sec.id ? "2px solid #3b82f6" : "2px solid transparent",
              background: "transparent", color: activeSection === sec.id ? "#3b82f6" : "#64748b",
              transition: "color 0.15s",
            }}
          >
            {sec.label}
          </button>
        ))}
      </div>

      {/* Section Content */}
      <div style={{ minHeight: 400 }}>
        {activeSection === "opinion" && (
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "#1e293b", marginBottom: 12 }}>
              Audit Opinion
            </h2>
            <div style={{
              background: "#f8fafc", padding: 20, borderRadius: 8,
              fontSize: 13, lineHeight: 1.7, color: "#334155",
              whiteSpace: "pre-wrap",
            }}>
              {report.opinion}
            </div>
          </div>
        )}

        {activeSection === "basis" && (
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "#1e293b", marginBottom: 12 }}>
              Basis for Opinion
            </h2>
            <div style={{
              background: "#f8fafc", padding: 20, borderRadius: 8,
              fontSize: 13, lineHeight: 1.7, color: "#334155",
              whiteSpace: "pre-wrap",
            }}>
              {report.basisForOpinion}
            </div>
            {report.emphasisOfMatter && (
              <div style={{
                marginTop: 16, padding: 12, borderRadius: 8,
                background: "#fffbeb", border: "1px solid #fde68a",
                fontSize: 13, lineHeight: 1.6, color: "#92400e",
              }}>
                <strong>Emphasis of Matter:</strong> {report.emphasisOfMatter}
              </div>
            )}
          </div>
        )}

        {activeSection === "kam" && (
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "#1e293b", marginBottom: 4 }}>
              Key Audit Matters
            </h2>
            <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 16 }}>
              Key audit matters are those matters that, in our professional judgement, were of most significance in our audit of the financial statements.
            </p>
            {report.keyAuditMatters.map((kam, idx) => (
              <div key={idx} style={{
                padding: 16, marginBottom: 12, borderRadius: 8,
                border: "1px solid #e2e8f0", background: "#fff",
              }}>
                <div style={{ display: "flex", gap: 10, marginBottom: 8 }}>
                  <span style={{
                    width: 24, height: 24, borderRadius: "50%", background: "#eff6ff",
                    color: "#3b82f6", fontSize: 12, fontWeight: 600,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    flexShrink: 0,
                  }}>
                    {idx + 1}
                  </span>
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: "#1e293b", margin: 0, paddingTop: 3 }}>
                    {kam.title}
                  </h3>
                </div>
                <div style={{ fontSize: 13, lineHeight: 1.6, color: "#475569", marginLeft: 34 }}>
                  {kam.detail}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeSection === "responsibilities" && (
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "#1e293b", marginBottom: 12 }}>
              Responsibilities
            </h2>

            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: "#475569", marginBottom: 8 }}>
                Responsibilities of Management and Those Charged with Governance
              </h3>
              <div style={{
                background: "#f8fafc", padding: 16, borderRadius: 8,
                fontSize: 13, lineHeight: 1.7, color: "#334155",
              }}>
                {report.responsibilities.entity}
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: "#475569", marginBottom: 8 }}>
                Auditor's Responsibilities for the Audit of the Financial Statements
              </h3>
              <div style={{
                background: "#f8fafc", padding: 16, borderRadius: 8,
                fontSize: 13, lineHeight: 1.7, color: "#334155",
              }}>
                {report.responsibilities.auditor}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        marginTop: 32, paddingTop: 16, borderTop: "1px solid #e2e8f0",
        fontSize: 11, color: "#94a3b8",
      }}>
        Report Reference: {report.id} &middot; Prepared in accordance with ISA 700 (Revised)
      </div>
    </div>
  );
};

export default ReportViewer;
