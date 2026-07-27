import React from "react";

interface WorkflowStep {
  id: string;
  agentName: string;
  status: "running" | "completed" | "failed" | "pending";
  duration: string;
  keyOutput: string;
}

const STATUS_CONFIG: Record<string, { dot: string; label: string }> = {
  running: { dot: "#3b82f6", label: "Running" },
  completed: { dot: "#16a34a", label: "Completed" },
  failed: { dot: "#dc2626", label: "Failed" },
  pending: { dot: "#94a3b8", label: "Pending" },
};

const MOCK_STEPS: WorkflowStep[] = [
  { id: "s1", agentName: "Planner", status: "completed", duration: "1.2s", keyOutput: "Generated 6 audit objectives, identified revenue recognition and lease accounting as high-risk areas." },
  { id: "s2", agentName: "Knowledge Agent", status: "completed", duration: "2.4s", keyOutput: "Retrieved 12 relevant regulatory citations (SAS-145, ASC 842, PCAOB AS 2401) from the ontology." },
  { id: "s3", agentName: "Risk Agent", status: "completed", duration: "3.1s", keyOutput: "Assessed 4 control areas; procurement and goodwill impairment flagged with moderate risk scores." },
  { id: "s4", agentName: "Evidence Agent", status: "running", duration: "4.7s", keyOutput: "Collecting supporting evidence for journal entries #1042-#1050 across 3 source systems..." },
  { id: "s5", agentName: "Reviewer", status: "pending", duration: "--", keyOutput: "Awaiting evidence collection to begin final review pass." },
];

const LINE_COLOR = "#e2e8f0";

const WorkflowMonitor: React.FC = () => {
  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif", maxWidth: 640 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0, marginBottom: 20 }}>Workflow Monitor</h1>
      <div style={{ position: "relative", paddingLeft: 32 }}>
        {/* vertical line */}
        <div
          style={{
            position: "absolute",
            left: 10,
            top: 8,
            bottom: 8,
            width: 2,
            background: LINE_COLOR,
            borderRadius: 1,
          }}
        />
        {MOCK_STEPS.map((step, idx) => {
          const cfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.completed;
          const isLast = idx === MOCK_STEPS.length - 1;
          return (
            <div key={step.id} style={{ position: "relative", paddingBottom: isLast ? 0 : 24 }}>
              {/* dot on the timeline */}
              <div
                style={{
                  position: "absolute",
                  left: -24,
                  top: 4,
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  background: cfg.dot,
                  border: step.status === "running" ? "2px solid #bfdbfe" : "none",
                  boxSizing: "border-box",
                  zIndex: 1,
                }}
              />
              {/* step card */}
              <div
                style={{
                  border: "1px solid #e2e8f0",
                  borderRadius: 8,
                  padding: 14,
                  background: step.status === "running" ? "#f0f9ff" : step.status === "pending" ? "#f8fafc" : "#fff",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: "#0f172a" }}>{step.agentName}</span>
                  <span style={{ fontSize: 12, color: "#64748b" }}>{step.duration}</span>
                  <span
                    style={{
                      marginLeft: "auto",
                      fontSize: 11,
                      fontWeight: 600,
                      color: cfg.dot,
                      background: `${cfg.dot}18`,
                      padding: "2px 8px",
                      borderRadius: 8,
                    }}
                  >
                    {cfg.label}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: 13, color: "#475569", lineHeight: 1.5 }}>{step.keyOutput}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default WorkflowMonitor;
