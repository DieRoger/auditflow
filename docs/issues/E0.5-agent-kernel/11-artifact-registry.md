# 0.5.3.3 — Artifact Registry（v3.2 新增）

- **Epic:** E0.5 Agent Kernel + Evaluation Core
- **Labels:** `agent-kernel`, `artifact`
- **Depends on:** 0.5.1.2

## Description
统一 Artifact 类型注册——后续 Service（Report Generator 等）不读自然语言，直接消费结构化 Artifact。所有 Agent/Service 产出必须是已注册 Artifact 类型，未注册类型拒绝序列化。

v3.2 冻结的 Artifact 类型：
- RiskFindingArtifact → risk_finding
- EvidencePackageArtifact → evidence_package
- KnowledgePackageArtifact → knowledge_package
- AuditPlanArtifact → audit_plan
- ReviewReportArtifact → review_report
- WorkpaperArtifact → workpaper
- ReportArtifact → audit_report

## Acceptance Criteria
- [ ] ArtifactRegistry：register / get / list_types
- [ ] 所有 Agent/Service 产出必须是已注册 Artifact 类型
- [ ] 未注册类型拒绝序列化
- [ ] Artifact Registry 可查询（Report Generator 按类型发现上游产出）
- [ ] v3.2 冻结的 7 种 Artifact 类型全部注册

## I/O Interface
```python
class ArtifactRegistry:
    """所有 Artifact 类型必须注册"""
    _registry: dict[str, type[AuditArtifact]] = {}

    def register(self, artifact_class: type[AuditArtifact]) -> None:
        """注册 Artifact 子类型"""
        ...

    def get(self, artifact_type: str) -> type[AuditArtifact]:
        """按 artifact_type 字符串获取对应的 Pydantic 类型"""
        ...

    def list_types(self) -> list[str]:
        """列出所有已注册的 artifact_type"""
        ...

# 注册的 Artifact 类型（v3.2 冻结）
# RiskFindingArtifact      → risk_finding
# EvidencePackageArtifact  → evidence_package
# KnowledgePackageArtifact → knowledge_package
# AuditPlanArtifact        → audit_plan
# ReviewReportArtifact     → review_report
# WorkpaperArtifact        → workpaper
# ReportArtifact           → audit_report
```

## Related ADR
ADR-001 — Agent Contract v1 (Artifact)
