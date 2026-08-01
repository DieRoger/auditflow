# AuditFlow — Agent 指南

## 架构原则

1. **Architecture First** — 设计先于编码
2. **Documentation Driven Development** — 文档驱动开发
3. **Evaluation Driven Development** — 评估驱动开发
4. **Human Always Has Final Authority** — 人类拥有最终决策权
5. **Every AI Output Must Be Traceable** — 所有 AI 输出必须可追溯

## Agent vs Service

| 类型 | 组件 | 说明 |
|------|------|------|
| Agent ✅ | Planner / Knowledge / Risk / Evidence / Reviewer | 需要自主决策循环 |
| Service | PlanningEngine / WorkpaperGenerator / ReportGenerator | 确定性计算 + 模板渲染 |

## 编码规范

- Python 3.11+, Ruff lint, MyPy strict mode
- Pytest + coverage ≥ 80%
- 所有 Agent 实现 BaseAgent 接口
- 所有输出须为 AuditArtifact 类型

详细规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。
