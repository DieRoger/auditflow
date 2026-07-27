"""Prompt Registry — Prompt 版本化管理 + Evaluation 绑定

Prompt 是 AI 系统最大的变化来源。
每次 Prompt 变更必须伴随 Evaluation，新版本低于基线则禁止激活。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PromptVersion(BaseModel):
    model_config = {"protected_namespaces": ()}
    """一个 Prompt 版本的完整记录"""
    agent_name: str
    version: str  # "v1", "v2"
    content: str  # Markdown 模板
    variables: list[str] = Field(default_factory=list)
    model_name: str = ""
    evaluation_score: float | None = None  # 当前 Benchmark 分数
    baseline_score: float | None = None  # 上一版本分数（首次为 None）
    improvement: float | None = None  # delta
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = False


class PromptRegistry:
    """Prompt 版本注册表

    所有 Agent 的 Prompt 必须通过此 Registry 管理。
    禁止直接修改 prompt 文件系统。
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[PromptVersion]] = {}

    def register(self, version: PromptVersion) -> None:
        """注册新 Prompt 版本

        自动计算 improvement 并执行版本保护：
        - 同版本不可覆盖
        - 已评估版本不可删除
        """
        agent = version.agent_name
        existing = self._versions.get(agent, [])

        # 检查版本重复
        if any(v.version == version.version for v in existing):
            raise ValueError(f"Agent '{agent}' 版本 '{version.version}' 已存在，禁止覆盖")

        # 自动计算 improvement
        if existing and version.evaluation_score is not None:
            latest = max(existing, key=lambda v: v.created_at)
            if latest.evaluation_score is not None:
                version.baseline_score = latest.evaluation_score
                version.improvement = round(version.evaluation_score - latest.evaluation_score, 4)

        self._versions.setdefault(agent, []).append(version)

    def activate(self, agent_name: str, version_str: str) -> PromptVersion:
        """激活指定版本

        检查：新版本的 evaluation_score >= baseline_score
        """
        versions = self._versions.get(agent_name, [])
        target = next((v for v in versions if v.version == version_str), None)
        if target is None:
            raise KeyError(f"Agent '{agent_name}' 版本 '{version_str}' 不存在")

        # 基线检查
        if (target.evaluation_score is not None and target.baseline_score is not None
                and target.evaluation_score < target.baseline_score):
            raise ValueError(
                    f"版本 '{version_str}' score={target.evaluation_score} "
                    f"低于基线 {target.baseline_score}，不可激活"
                )

        # 去激活其他版本
        for v in versions:
            v.is_active = False

        target.is_active = True
        return target

    def get_active(self, agent_name: str) -> PromptVersion | None:
        """获取当前激活的 Prompt 版本"""
        versions = self._versions.get(agent_name, [])
        return next((v for v in versions if v.is_active), None)

    def get_history(self, agent_name: str) -> list[PromptVersion]:
        """获取版本历史（按时间降序）"""
        versions = self._versions.get(agent_name, [])
        return sorted(versions, key=lambda v: v.created_at, reverse=True)

    def compare_versions(self, agent_name: str, v1: str, v2: str) -> dict:
        """比较两个版本的指标差异"""
        versions = self._versions.get(agent_name, [])
        ver_a = next((v for v in versions if v.version == v1), None)
        ver_b = next((v for v in versions if v.version == v2), None)
        if not ver_a or not ver_b:
            raise KeyError(f"版本 {v1} 或 {v2} 不存在")
        return {
            "agent": agent_name,
            "v1": {"version": v1, "score": ver_a.evaluation_score, "model": ver_a.model_name},
            "v2": {"version": v2, "score": ver_b.evaluation_score, "model": ver_b.model_name},
            "delta": round(ver_b.evaluation_score - ver_a.evaluation_score, 4)
            if ver_a.evaluation_score is not None and ver_b.evaluation_score is not None
            else None,
        }
