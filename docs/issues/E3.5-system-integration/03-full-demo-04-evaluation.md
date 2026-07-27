# 03 — Full Integration Demo

**父 Issue：** E3.5 System Bring-up
**优先级：** P1（依赖 01 + 02）
**预计工作量：** 2-3 天

## 目标

将 Workflow Engine + Document Pipeline + 5 Agent + Evidence Engine 全部串联：

```
上传 PDF（Tesla 10-K 收入确认章节）
  → Document Pipeline（解析 → Chunk → PGVector）
  → Workflow Engine Start
  → Planner: 拆解审计任务
  → Knowledge: 从 PGVector 检索相关准则
  → Risk: 识别收入确认风险
  → Evidence: 从文档 Chunk 匹配证据 → Citation
  → Reviewer: 审查质量 → 生成 Review Report
  → Workpaper Generator: 生成审计工作底稿
  → 前端 Timeline 展示全流程
```

## 验收标准

1. 完整流程无人工干预跑通（除 Reviewer HITL 外）
2. Risk 输出包含至少 1 条 Citation（document_id + page + excerpt）
3. Workpaper 包含 Risk → Evidence → Procedure 的完整链条
4. 前端 Dashboard 能看到 Workflow 状态变化

## 产出物

1. `scripts/full_demo.py` — 完整演示脚本
2. 演示录屏/截图

---

# 04 — Retrieval & Evidence & Evaluation

**父 Issue：** E3.5 System Bring-up
**优先级：** P1（依赖 01 + 02）
**预计工作量：** 3-5 天

## 目标

建立可量化的质量评估体系。

### 4.1 Retrieval 评估

- 准备 100 个审计 QA 对（覆盖收入确认、存货、减值、关联交易等领域）
- 跑 Keyword / Vector / Hybrid 三种检索
- 统计 Recall@5、MRR、Citation Accuracy
- 建立 Baseline 报告

### 4.2 Evidence 验证

- 打通 Evidence Package → Citation → Grounding Checker
- 每个 Risk 必须有 Evidence → Page → Confidence
- Grounding Checker 对 Agent Claim 做事后验证

### 4.3 Evaluation Runner

- 接入现有 `evaluation/runner.py`
- 对每次 Prompt 变更自动跑 Evaluation
- 建立指标趋势 Dashboard

## 验收标准

1. Recall@5 有量化数字（不要求特定值，先有 Baseline）
2. Grounding Checker 能对 5 条 Agent Claim 给出 PASS/FAIL 判定
3. Evaluation Runner 可一键运行并输出报告

## 不做的事

- 不追求特定 Recall 指标（先建立 Baseline）
- 不新增 Prompt（先用现有 Prompt 评估）
