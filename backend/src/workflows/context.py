"""Context Manager — Agent 执行上下文组装与压缩"""

from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class AgentContext(BaseModel):
    """Agent 执行期的完整上下文"""
    workflow_id: str = ""
    project_id: str = ""
    engagement_id: str = ""
    upstream_artifacts: list[dict] = Field(default_factory=list, description="上游 Agent 产出的 Artifact 列表")
    conversation_history: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list, description="检索到的相关证据")
    token_count: int = 0


class ContextManager:
    """上下文管理器 — 组装、压缩、注入上下文"""

    MAX_TOKENS_DEFAULT = 8000

    async def build_context(
        self, workflow_id: str, agent_name: str,
        upstream_results: dict[str, Any],
        memory: dict[str, Any] | None = None,
    ) -> AgentContext:
        """为指定 Agent 组装执行上下文"""
        artifacts = []
        for node_id, result in upstream_results.items():
            artifact = result.get("artifact", {})
            if artifact:
                artifacts.append({
                    "node_id": node_id,
                    "artifact_type": artifact.get("artifact_type", "unknown"),
                    "summary": self._summarize_artifact(artifact),
                })

        ctx = AgentContext(
            workflow_id=workflow_id,
            upstream_artifacts=artifacts,
            memory=memory or {},
        )
        logger.info("context_built", agent=agent_name, artifacts=len(artifacts))
        return ctx

    async def compress(self, context: AgentContext, max_tokens: int = MAX_TOKENS_DEFAULT) -> AgentContext:
        """压缩上下文（超过 token 限制时裁剪）"""
        if context.token_count <= max_tokens:
            return context

        # 裁剪策略：保留最近 3 条对话历史
        if len(context.conversation_history) > 3:
            context.conversation_history = context.conversation_history[-3:]
        logger.info("context_compressed", from_tokens=context.token_count, to_tokens=context.token_count)
        return context

    def _summarize_artifact(self, artifact: dict) -> dict:
        """生成 Artifact 摘要（用于上下文）"""
        atype = artifact.get("artifact_type", "unknown")
        content = artifact.get("content", {})
        if atype == "risk_finding":
            return {"type": "risk", "area": content.get("area", ""), "severity": content.get("severity", "")}
        if atype == "finding":
            findings = content.get("findings", [])
            return {
                "type": "anomaly",
                "findings_total": content.get("total", len(findings)),
                "severity_summary": content.get("summary", {}),
                "top_findings": [
                    {"risk": f.get("risk_type", ""), "severity": f.get("severity", ""),
                     "score": f.get("score", 0)} for f in findings[:5]
                ],
            }
        if atype == "evidence_package":
            return {"type": "evidence", "coverage": content.get("coverage", 0)}
        if atype == "review_report":
            return {"type": "review", "quality_score": content.get("quality_score", 0), "result": content.get("review_result", "")}  # noqa: E501
        return {"type": atype}
