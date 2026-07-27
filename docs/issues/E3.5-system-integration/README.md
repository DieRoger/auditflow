# E3.5 — System Bring-up（系统集成阶段）

**状态：** 计划中
**优先级：** P0 — 最高
**目标：** 将已开发的独立模块串联为一条稳定、可观测、可评估的审计闭环。

## 背景

项目已越过了"模块开发"阶段。以下能力均已具备独立实现：

- ✅ 5 个 Agent（Planner / Knowledge / Risk / Evidence / Reviewer）均可独立调用 DeepSeek
- ✅ Workflow Engine（8494 行）实现状态机、Trace、Checkpoint、HITL
- ✅ AgentRegistry + ToolRegistry + 权限控制
- ✅ Document Pipeline：Upload → Parser → OCR → Embedding → PGVector
- ✅ Evidence Collector + Grounding Checker
- ✅ Hybrid Search（Keyword + Vector + Reranker）
- ✅ 前端 8 个页面组件

**核心问题：** 这些模块各自能跑，但从未被一起跑通过。
`demo_v0.py` 是唯一端到端脚本——它绕过了 Workflow Engine、Registry、Event Bus 和 Trace。

**核心目标：** 不再新增任何能力。证明已有能力能协同工作。

## 原则

1. **验证优先于开发。** 在写任何新代码前，先证明已有代码能跑通。
2. **所有 Agent 通过 Workflow Engine 驱动。** 不允许 `demo_v0.py` 式的直接实例化。
3. **所有输出必须可观测。** Trace / Event / Citation 是必选项，不是可选项。
4. **Ontology 保持 SQL Graph Ready。** 不引入 Neo4j，待真正需要时再迁移。

## Issue 清单

| # | Issue | 目标 | 验证标准 |
|---|-------|------|---------|
| 01 | Workflow Engine 接管 5 Agent | Workflow Engine 驱动全管线 | `bringup.py` 可重现运行 |
| 02 | Pipeline Validation | PDF → Chunk → PGVector 全链路 | 数据库有 chunk 且 embedding 非空 |
| 03 | Full Integration Demo | 上传 PDF → 审计报告 | 端到端流程完整闭环 |
| 04 | Retrieval & Evidence & Evaluation | 指标驱动质量提升 | Recall@5 可量化追踪 |

## 不做的事

- ❌ 不新增第 6 个 Agent
- ❌ 不引入 Neo4j
- ❌ 不优化 Prompt（先用现有 Prompt 跑通再调优）
- ❌ 不新增前端页面（用现有页面验证即可）
