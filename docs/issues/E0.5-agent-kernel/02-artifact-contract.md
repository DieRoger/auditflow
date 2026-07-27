# 0.5.1.2 — Artifact Contract

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `contract`
- **Depends on:** 0.5.1.1

## Description
AuditArtifact 基类 + RiskFinding / EvidencePackage / AuditPlan / ReviewReport 具体类型（见 ISSUES.md §Artifact Contract）。所有 Agent/Service 的结构化产出必须继承 AuditArtifact，而非 text blob。artifact_type 标识产出类型，parent_artifact_id 形成溯源链。

## Acceptance Criteria
- [ ] AuditArtifact 基类：artifact_type / artifact_id / created_by / schema_version / content / citations / parent_artifact_id
- [ ] RiskFindingArtifact（risk_finding）：area / title / severity / probability / indicators / related_standards / suggested_procedures / reasoning
- [ ] EvidencePackageArtifact（evidence_package）：claims / coverage / unmatched
- [ ] AuditPlanArtifact（audit_plan）：materiality / sampling_strategy / procedures / timeline
- [ ] ReviewReportArtifact（review_report）：review_result / issues / quality_score
- [ ] 所有 Agent 输出必须是 Artifact 子类型
- [ ] Pydantic 序列化/反序列化验证
- [ ] parent_artifact_id 溯源链完整性

## I/O Interface
```python
class AuditArtifact(BaseModel):
    """所有 Agent/Service 的结构化产出 — 不是 text blob"""
    artifact_type: str          # "risk_finding" | "evidence_package" | "audit_plan" | ...
    artifact_id: str
    created_by: str             # agent_name
    schema_version: str         # "v1"
    content: dict               # 结构化 JSON
    citations: list[Citation]
    parent_artifact_id: str | None  # 溯源链

class RiskFindingArtifact(AuditArtifact):
    artifact_type: Literal["risk_finding"]
    content: RiskFindingContent

class RiskFindingContent(BaseModel):
    area: str
    title: str
    severity: str               # CRITICAL | HIGH | MEDIUM | LOW
    probability: float
    indicators: list[str]
    related_standards: list[str]
    suggested_procedures: list[ProcedureSuggestion]
    reasoning: list[str]        # Agent 推理链

class EvidencePackageArtifact(AuditArtifact):
    artifact_type: Literal["evidence_package"]
    content: EvidencePackageContent

class EvidencePackageContent(BaseModel):
    claims: list[EvidencedClaim]
    coverage: float             # 有证据的 claim / 总 claim
    unmatched: list[str]

class AuditPlanArtifact(AuditArtifact):
    artifact_type: Literal["audit_plan"]
    content: AuditPlanContent

class AuditPlanContent(BaseModel):
    materiality: MaterialityCalc
    sampling_strategy: SamplingStrategy
    procedures: list[ProcedureDef]
    timeline: dict

class ReviewReportArtifact(AuditArtifact):
    artifact_type: Literal["review_report"]
    content: ReviewReportContent

class ReviewReportContent(BaseModel):
    review_result: str          # APPROVED | NEEDS_REVISION | REJECTED
    issues: list[ReviewIssue]
    quality_score: float
```

## Related ADR
ADR-001 — Agent Contract v1 (Artifact)
