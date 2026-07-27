"""Agent 结构化产出 — Artifact Contract

所有 Agent/Service 产出必须是 AuditArtifact 子类型，而非 text blob。
Service（ReportGenerator / WorkpaperComposer）直接消费结构化 Artifact。
"""

from typing import Literal

from pydantic import BaseModel, Field

from .contracts import Citation


class AuditArtifact(BaseModel):
    """所有 Artifact 的基类"""
    __artifact_type__: str = ""  # 类级别标识符，子类覆盖
    artifact_type: str
    artifact_id: str
    created_by: str  # agent_name
    schema_version: str = "v1"
    content: dict = Field(default_factory=dict)
    citations: list[Citation] = Field(default_factory=list)
    parent_artifact_id: str | None = None


# ── RiskFindingArtifact ──────────────────────────────────────────

class ProcedureSuggestion(BaseModel):
    type: str  # Inspection | Confirmation | Recalculation | ...
    target: list[str]
    steps: list[str]
    evidence_required: list[str]


class RiskFindingContent(BaseModel):
    area: str
    title: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    probability: float = Field(ge=0.0, le=1.0)
    indicators: list[str] = Field(default_factory=list)
    related_standards: list[str] = Field(default_factory=list)
    suggested_procedures: list[ProcedureSuggestion] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list, description="Agent 推理链")


class RiskFindingArtifact(AuditArtifact):
    __artifact_type__ = "risk_finding"
    artifact_type: Literal["risk_finding"] = "risk_finding"
    content: RiskFindingContent


# ── EvidencePackageArtifact ──────────────────────────────────────

class EvidencedSource(BaseModel):
    document_id: str
    page: int | None = None
    excerpt: str


class EvidencedClaim(BaseModel):
    claim: str
    matched: bool
    source: EvidencedSource | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class EvidencePackageContent(BaseModel):
    claims: list[EvidencedClaim] = Field(default_factory=list)
    coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="有证据的 claim / 总 claim")
    unmatched: list[str] = Field(default_factory=list)


class EvidencePackageArtifact(AuditArtifact):
    __artifact_type__ = "evidence_package"
    artifact_type: Literal["evidence_package"] = "evidence_package"
    content: EvidencePackageContent


# ── AuditPlanArtifact ────────────────────────────────────────────

class MaterialityCalc(BaseModel):
    overall: str  # e.g. "$5M (1% of total assets)"
    performance: str  # e.g. "$3.75M (75% of overall)"
    basis: str  # e.g. "Total Assets"


class SamplingStrategy(BaseModel):
    population: int
    sample_size: int
    method: str  # MUS | Stratified | Random


class ProcedureDef(BaseModel):
    procedure_id: str
    target_risk_id: str
    assertion: str
    steps: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    budget_hours: int = 0


class AuditPlanContent(BaseModel):
    materiality: MaterialityCalc
    sampling_strategy: SamplingStrategy | None = None
    procedures: list[ProcedureDef] = Field(default_factory=list)
    timeline: dict = Field(default_factory=dict)


class AuditPlanArtifact(AuditArtifact):
    __artifact_type__ = "audit_plan"
    artifact_type: Literal["audit_plan"] = "audit_plan"
    content: AuditPlanContent


# ── ReviewReportArtifact ─────────────────────────────────────────

class ReviewIssue(BaseModel):
    severity: str  # HIGH | MEDIUM | LOW
    issue_type: str  # UNSUPPORTED_CLAIM | MISSING_CITATION | WEAK_LOGIC | HALLUCINATION
    location: str
    description: str
    suggestion: str = ""


class ReviewReportContent(BaseModel):
    review_result: str  # APPROVED | NEEDS_REVISION | REJECTED
    issues: list[ReviewIssue] = Field(default_factory=list)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_risk: float = Field(default=0.0, ge=0.0, le=1.0)


class ReviewReportArtifact(AuditArtifact):
    __artifact_type__ = "review_report"
    artifact_type: Literal["review_report"] = "review_report"
    content: ReviewReportContent


# ── Artifact 类型注册表 ──────────────────────────────────────────

ARTIFACT_REGISTRY: dict[str, type[AuditArtifact]] = {
    "risk_finding": RiskFindingArtifact,
    "evidence_package": EvidencePackageArtifact,
    "audit_plan": AuditPlanArtifact,
    "review_report": ReviewReportArtifact,
}


class ArtifactRegistry:
    """Artifact 类型注册表 — 统一注册与发现"""

    def __init__(self) -> None:
        self._registry: dict[str, type[AuditArtifact]] = {}

    def register(self, artifact_class: type[AuditArtifact]) -> None:
        """注册 Artifact 子类型"""
        atype = getattr(artifact_class, "__artifact_type__", None)
        if not atype:
            raise ValueError(f"Artifact 类 {artifact_class.__name__} 未定义 __artifact_type__")
        if atype in self._registry:
            raise ValueError(f"Artifact 类型 '{atype}' 已注册")
        self._registry[atype] = artifact_class

    def get(self, artifact_type: str) -> type[AuditArtifact]:
        """按 artifact_type 获取对应的 Pydantic 类型"""
        cls = self._registry.get(artifact_type)
        if cls is None:
            raise KeyError(f"Artifact 类型 '{artifact_type}' 未注册")
        return cls

    def list_types(self) -> list[str]:
        """列出所有已注册的 artifact_type"""
        return list(self._registry.keys())

    @classmethod
    def create_default(cls) -> "ArtifactRegistry":
        """创建包含 v3.2 冻结的 7 种 Artifact 类型的 Registry"""
        registry = cls()
        registry.register(RiskFindingArtifact)
        registry.register(EvidencePackageArtifact)
        # registry.register(KnowledgePackageArtifact)  # E3 实现
        registry.register(AuditPlanArtifact)
        registry.register(ReviewReportArtifact)
        # registry.register(WorkpaperArtifact)  # E4 实现
        # registry.register(ReportArtifact)  # E4 实现
        return registry
