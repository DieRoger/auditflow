# AuditFlow 评估指标体系 —— 四层评估系统

> **版本:** v1.0
> **对应 Epic:** E0.5 → E2 → E3 → E4（贯穿全生命周期）
> **维护者:** AuditFlow 核心团队
> **最后更新:** 2026-01

---

## 目录

1. [概述：Evaluation Driven Development](#1-概述evaluation-driven-development)
2. [Layer 1 — Retrieval Evaluation（检索评估）](#2-layer-1--retrieval-evaluation检索评估)
3. [Layer 2 — Agent Evaluation（Agent 评估）](#3-layer-2--agent-evaluationagent-评估)
4. [Layer 3 — Grounding Evaluation（事实依据评估）](#4-layer-3--grounding-evaluation事实依据评估)
5. [Layer 4 — Workflow Evaluation（工作流评估）](#5-layer-4--workflow-evaluation工作流评估)
6. [EvaluationRunner 与 Experiment Tracker 接口](#6-evaluationrunner-与-experiment-tracker-接口)
7. [Baseline 对比与 PR 门禁](#7-baseline-对比与-pr-门禁)

---

## 1. 概述：Evaluation Driven Development

在 AuditFlow 中，**没有任何 Agent 或 Service 在 Benchmark 评分达标之前被视为"完成"**。这是审计场景对质量要求的铁律：每个组件必须在标准化数据集上通过量化指标验证，而非仅靠代码审查或手动测试。

### 1.1 四层评估全景

```
┌──────────────────────────────────────────────────────────────────────┐
│                     AuditFlow 四层评估体系                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  L4 ─ Workflow Evaluation                                            │
│       Completion Rate · Human Intervention Count · Time Reduction    │
│       触发时机：E4 end-to-end workflow 完成                           │
│                                                                      │
│  L3 ─ Grounding Evaluation                                           │
│       Citation Precision · Citation Recall · Unsupported Claim Rate  │
│       触发时机：E2 GroundingChecker 完成                              │
│                                                                      │
│  L2 ─ Agent Evaluation (per Agent)                                   │
│       Planner: Plan Completeness, Ontology Alignment                 │
│       Knowledge: Precision@5, Citation Accuracy                      │
│       Risk: Risk Classification Accuracy, Severity Accuracy,         │
│             Reasoning Quality                                        │
│       Evidence: Evidence Coverage, Citation Source Accuracy           │
│       Reviewer: Issue Detection Rate, False Positive Rate            │
│       触发时机：每个 Agent 开发期间（E3）                              │
│                                                                      │
│  L1 ─ Retrieval Evaluation                                           │
│       Recall@5 · Recall@20 · MRR · NDCG@10                          │
│       触发时机：E2 完成                                               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **分层解耦** | 每一层评估可独立运行，不依赖上层结果 |
| **指标正交** | 各层指标互不重叠，避免一个 bug 影响多个分数 |
| **自动化** | 所有指标由 EvaluationRunner 自动计算，零人工干预 |
| **可复现** | 同一 Prompt 版本 + 同一 Model → 相同 Benchmark → 相同分数 |
| **门禁化** | 任何新版本分数 < Baseline → PR 被自动 Block |

### 1.3 Layer 与 Epic 对应关系

| Layer | 名称 | 开发 Epic | 数据来源 | 执行频率 |
|-------|------|----------|----------|----------|
| L1 | Retrieval | E2 | E7 Benchmark 标注段落 | 每次 PR |
| L2 | Agent | E3 | Benchmark `expected` 标注 | 每次 PR |
| L3 | Grounding | E2 | GroundingChecker + Benchmark 标准引用 | 每次 PR |
| L4 | Workflow | E4 | 端到端真实案例执行记录 | 每周 Cron |

---

## 2. Layer 1 — Retrieval Evaluation（检索评估）

### 2.1 概述

Layer 1 是最底层的评估，仅关注 **文档检索子系统** 是否能从文档库中找到正确的段落。它不涉及任何 LLM 推理或 Agent 决策——纯粹衡量向量检索 / 关键词检索 / 混合检索的召回能力。

**触发时机：** E2（Retrieval & Evidence Engine）完成时。

**数据来源：** E7 Benchmark Dataset 中每个 Case 的 `documents[].pages` 字段标注了关键页码，这些页码对应的文档段落即为检索的 ground truth。

### 2.2 指标体系

| 指标 | 英文名 | 公式 / 含义 | 理想值 |
|------|--------|------------|--------|
| **Recall@5** | Recall at 5 | 前 5 个结果中包含正确段落的 Case 比例 | ≥ 0.85 |
| **Recall@20** | Recall at 20 | 前 20 个结果中包含正确段落的 Case 比例 | ≥ 0.95 |
| **MRR** | Mean Reciprocal Rank | 第一个正确段落排名的倒数之均值：$\frac{1}{\|Q\|}\sum_{i}\frac{1}{\text{rank}_i}$ | ≥ 0.70 |
| **NDCG@10** | Normalized Discounted Cumulative Gain at 10 | 考虑排序位置加权的归一化折损累积增益 | ≥ 0.75 |

### 2.3 Recall@5 / Recall@20

```
Recall@K = (在前 K 个检索结果中命中至少一个正确段落的查询数) / (总查询数)
```

- **Recall@5** 衡量"第一页结果"的质量——用户在首屏是否能看到相关段落。
- **Recall@20** 衡量"宽召回"能力——相关段落是否被检索系统捕获（即使排在靠后位置）。

在 AuditFlow 上下文中，每个 Benchmark Case 的 `documents[].pages` 标注了关键页码。EvaluationRunner 将每个 Case 视为一个查询，将标注页码对应的段落作为 ground truth，检查检索结果中是否包含这些段落。

### 2.4 MRR（Mean Reciprocal Rank）

MRR 关注**第一个正确段落的排名位置**，排名越靠前，分数越高。与 Recall@K 不同，MRR 对排序质量敏感——即使两个系统 Recall@20 相同，MRR 也会区分出"正确结果排在第 1 位"与"正确结果排在第 19 位"的差异。

```
MRR = (1/排名1 + 1/排名2 + ... + 1/排名N) / N

示例：
  Case A: 第一个正确段落排名 1 → 贡献 1.0
  Case B: 第一个正确段落排名 3 → 贡献 0.333
  Case C: 第一个正确段落排名 10 → 贡献 0.1
  MRR = (1.0 + 0.333 + 0.1) / 3 = 0.478
```

### 2.5 NDCG@10

NDCG 衡量**前 10 个结果的排序质量**，引入分级相关性（而非简单的相关/不相关二分）。在 AuditFlow 中：

- 标注段落（ground truth）标记为相关性 2（高相关）
- 标注段落所在章节的其他段落标记为相关性 1（部分相关）
- 其余段落标记为相关性 0（不相关）

NDCG 对排序中高相关段落靠前的系统给予更高分数。

### 2.6 评估执行

```python
# L1 评估执行伪代码
class RetrievalEvaluator:
    """Layer 1 评估器 — 独立于 Agent 链"""

    async def evaluate(
        self,
        benchmark: BenchmarkSuite,
        retrieval_system: RetrievalSystem,
    ) -> RetrievalReport:
        metrics = {"Recall@5": [], "Recall@20": [], "MRR": [], "NDCG@10": []}
        for case in benchmark.cases:
            ground_truth = self._get_annotated_paragraphs(case)
            results = await retrieval_system.search(case.query)
            metrics["Recall@5"].append(recall_at_k(results, ground_truth, k=5))
            metrics["Recall@20"].append(recall_at_k(results, ground_truth, k=20))
            metrics["MRR"].append(mean_reciprocal_rank(results, ground_truth))
            metrics["NDCG@10"].append(ndcg_at_k(results, ground_truth, k=10))
        return RetrievalReport(
            metrics={k: mean(v) for k, v in metrics.items()},
            per_case=metrics,
        )
```

---

## 3. Layer 2 — Agent Evaluation（Agent 评估）

### 3.1 概述

Layer 2 是**最精细化的评估层**——每个 Agent 拥有独立的评估维度和指标，因为 Planner 的职责（任务拆解）与 Risk 的职责（风险分类）完全不同，不能用同一套标准衡量。

**触发时机：** 每个 Agent 开发期间（E3 Agent Core Runtime）。Agent 开发者在实现 Agent 逻辑的同时，必须为对应 Agent 配置评估用例并拿到达标分数。

**数据来源：** Benchmark Dataset 中各 Case 的 `expected` 字段。

### 3.2 Planner Agent 指标

Planner Agent 负责基于 Ontology 推理链拆解审计任务。

| 指标 | 英文名 | 含义 | 计算方式 | 通过阈值 |
|------|--------|------|----------|----------|
| **Plan Completeness** | 计划完整性 | Planner 产出的子任务是否覆盖了 Benchmark 标注的所有关键审计领域 | 覆盖的子任务数 / 标注子任务数 | ≥ 0.80 |
| **Ontology Alignment** | 本体对齐度 | Planner 选择的 Reasoning Chain 与标注链条的匹配程度 | 匹配的 Chain 节点数 / 标注 Chain 节点数 | ≥ 0.75 |

**Plan Completeness 详解：** Benchmark `expected` 中列出了受影响的 assertions 和建议的 procedures。Planner 需要在其 Audit Plan 中覆盖所有这些领域——遗漏任何一项都会降低 Completeness 分数。

**Ontology Alignment 详解：** E1B 构建的 Ontology Reasoning Chain（Risk → Assertion → Procedure → Evidence → Standard）是 Planner 的导航地图。Alignment 衡量 Planner 选择的推理路径与 Benchmark 标注路径的重合度。

### 3.3 Knowledge Agent 指标

Knowledge Agent 负责检索并引用审计准则/会计准则。

| 指标 | 英文名 | 含义 | 计算方式 | 通过阈值 |
|------|--------|------|----------|----------|
| **Precision@5** | 标准检索精度 | 前 5 个检索到的准则段落中，与 Case 真正相关的比例 | 相关段落数 / 5 | ≥ 0.70 |
| **Citation Accuracy** | 引用准确性 | Knowledge Agent 引用的准则段落是否精确（段落号、条款内容） | 正确引用数 / 总引用数 | ≥ 0.85 |

**Precision@5 说明：** 不同于 L1 的 Recall@5（关心"是否找到了"），Knowledge Agent 的 Precision@5 关心"找到的是否都有用"。因为审计准则检索的噪音成本很高——引用无关准则会误导下游 Risk Agent。

**Citation Accuracy 说明：** 不仅要求引用的准则段落号正确（如 "IFRS 15 ¶27"），还要求该段落的主题确实与当前 Case 的审计风险相关。

### 3.4 Risk Agent 指标

Risk Agent 是 AuditFlow 的核心决策 Agent，负责风险识别、分类、严重程度判定和推理过程输出。

| 指标 | 英文名 | 含义 | 计算方式 | 通过阈值 |
|------|--------|------|----------|----------|
| **Risk Classification Accuracy** | 风险分类准确率 | 识别出的风险领域与标注是否一致 | 正确分类的风险数 / 标注风险总数 | ≥ 0.80 |
| **Severity Accuracy** | 严重程度准确率 | 风险严重程度（CRITICAL/HIGH/MEDIUM/LOW）与标注是否一致 | 严重程度正确的风险数 / 标注风险总数 | ≥ 0.75 |
| **Reasoning Quality** | 推理质量 | LLM 辅助评估 + 人工抽查：推理逻辑是否自洽、是否引用充分证据 | 1–5 Likert 评分 | ≥ 3.5 |

**Risk Classification Accuracy 详解：**

```
Risk Classification Accuracy = |标注风险 ∩ 识别风险| / |标注风险|

示例：
  标注风险: [Revenue Recognition, AR Impairment, Inventory Valuation]
  识别风险: [Revenue Recognition, Inventory Valuation, Going Concern]
  匹配:      [Revenue Recognition, Inventory Valuation]        → 2 个
  Accuracy = 2/3 = 0.667  → 低于阈值，不合格
```

注意：额外识别出的风险（如上例中的 Going Concern）不计入分母——我们惩罚遗漏，但不惩罚"多发现"（多发现的风险由 Reviewer Agent 进一步评估其合理性）。

**Severity Accuracy 详解：**

```
Severity Accuracy = 严重程度匹配的风险数 / 标注风险总数

严重程度匹配规则：
  - CRITICAL 和 HIGH 之间的混淆 → 不匹配（视为误判）
  - MEDIUM 和 LOW 之间的混淆 → 不匹配
  - 两个方向偏移（如标注 HIGH 但判 LOW）→ 严重不匹配，扣除额外惩罚分
```

**Reasoning Quality 详解：** 这是唯一包含 LLM-as-Judge 的指标。评估流程：

1. 将 Risk Agent 的推理输出 + Benchmark 标注的 `expected.risks[].description` 发送给独立的评估 LLM
2. 评估 LLM 按 5 分 Likert 量表评分（1 = 推理完全错误，5 = 推理完美）
3. 随机抽取 20% 的评分结果进行人工复核
4. 若人工复核与 LLM 评分偏差 > 1 分，触发全量人工复核

### 3.5 Evidence Agent 指标

Evidence Agent 负责收集、筛选审计证据。

| 指标 | 英文名 | 含义 | 计算方式 | 通过阈值 |
|------|--------|------|----------|----------|
| **Evidence Coverage** | 证据覆盖度 | 收集的证据是否覆盖了所有标注的证据类型 | 已收集证据类型数 / 标注证据类型数 | ≥ 0.70 |
| **Citation Source Accuracy** | 引源准确率 | 证据引用的来源文档和位置是否正确 | 正确引用源 / 总引用源 | ≥ 0.80 |

**Evidence Coverage 详解：** Benchmark `expected` 中通过 `procedures` 字段标注了应该收集的证据类型（如 Inspection of sales_contracts、Confirmation of top5_customers）。Evidence Agent 必须为每个标注 procedure 收集到对应证据。

### 3.6 Reviewer Agent 指标

Reviewer Agent 负责审查上游 Agent 的全部输出，质疑不合理之处并决定是否退回。

| 指标 | 英文名 | 含义 | 计算方式 | 通过阈值 |
|------|--------|------|----------|----------|
| **Issue Detection Rate** | 问题检出率 | Reviewer 是否发现了 Benchmark 中预设的"已知错误" | 检出的已知错误数 / 预设错误总数 | ≥ 0.80 |
| **False Positive Rate** | 误报率 | Reviewer 标记为"有问题"但实际正确的比例 | 误报数 / 总报出数 | ≤ 0.15 |

**已知错误注入：** Benchmark 的某些 Case 会包含预设的"错误输出"——例如 Risk Agent 可能被注入一个故意错误的 severity 判定。Reviewer 的 Issue Detection Rate 衡量其发现这些已知错误的能力。

**False Positive Rate：** Reviewer 不能过于激进——将正确的输出标记为错误会阻塞工作流，造成不必要的 Human Review 开销。

---

## 4. Layer 3 — Grounding Evaluation（事实依据评估）

### 4.1 概述

Layer 3 关注所有 Agent **输出声明的可验证性**——每一条声称是否都有源自文档或准则段落的引用支撑。这是审计场景的核心合规要求：审计意见必须有据可查（ISA 500 ¶6）。

**触发时机：** E2 GroundingChecker 完成时。GroundingChecker 是一个独立 Service（非 Agent），在所有 Agent 输出生成后运行，对产出进行事实核查。

**数据来源：** 所有 Agent 的最终输出（Artifact）+ Benchmark 标准引用段落。

### 4.2 指标体系

| 指标 | 英文名 | 含义 | 计算方式 | 通过阈值 |
|------|--------|------|----------|----------|
| **Citation Precision** | 引用精确率 | 给出的引用中，真正支撑其 Claim 的比例 | 正确引用数 / 总引用数 | ≥ 0.85 |
| **Citation Recall** | 引用召回率 | Benchmark 标注的标准引用中，被 Agent 实际引用的比例 | 实际引用数 / 应引用总数 | ≥ 0.80 |
| **Unsupported Claim Rate** | 无依据声称率 | Agent 输出中没有任何引用支撑的 Claim 比例 | 无引用 Claim 数 / 总 Claim 数 | ≤ 0.10 |
| **Hallucination Rate** | 幻觉率 | 给出了引用但引用内容完全不支持该 Claim 的比例 | 幻觉 Claim 数 / 总 Claim 数 | ≤ 0.05 |

### 4.3 Citation Precision

```
Citation Precision = |{引用: 引用内容确实支撑其 Claim}| / |{所有给出的引用}|

示例：
  Agent 声称: "收入确认存在重大风险 (IFRS 15 ¶27, ISA 240 ¶32)"
  GroundingChecker 验证:
    - IFRS 15 ¶27 确实讨论收入确认 → ✓
    - ISA 240 ¶32 讨论舞弊风险 → ✓
  → 两个引用都匹配 → Precision = 2/2 = 1.0
```

### 4.4 Citation Recall

```
Citation Recall = |{Agent 实际引用的标准引用}| / |{Benchmark 标注的标准引用}|

示例：
  Benchmark 标注: [IFRS 15 ¶27, IFRS 15 ¶31, ISA 240 ¶32, ISA 500 ¶6]
  Agent 实际引用: [IFRS 15 ¶27, ISA 240 ¶32]
  → Recall = 2/4 = 0.50  → 遗漏了两个关键准则，不合格
```

### 4.5 Unsupported Claim Rate

```
Unsupported Claim Rate = |{Claim: 没有任何 citation 支撑}| / |{所有 Claim}|

Claim 定义：Agent 输出中任何事实性陈述（排除纯结构性/格式性文本）。
Unsupported Claim 定义：Claim 没有附带任何 citation，或附带 citation 但引用段落与 Claim 无关。

示例：
  "应收账款周转天数从 90 天上升到 120 天 [来源: ar_aging_report.xlsx]" → 有引用 ✓
  "该行业平均增长率为 10%" → 无引用 ✗ (Unsupported)
```

### 4.6 Hallucination Rate

Hallucination Rate 比 Unsupported Claim Rate 更严重——Agent 不仅给出了引用，而且引用的内容**完全无法**支撑其 Claim。这是"捏造引用"行为。

```
Hallucination Rate = |{Claim: 引用完全无法支撑}| / |{所有 Claim}|

示例：
  Agent 声称: "IFRS 15 ¶27 要求所有收入必须在发货时确认"
  实际 IFRS 15 ¶27: "An entity shall account for a contract... only when all of the following criteria are met..."
  → 引用的准则段落完全不支持 Agent 的声称 → Hallucination
```

### 4.7 GroundingChecker 执行流程

```
┌──────────────────────────────────────────────────────────────────┐
│  GroundingChecker（独立 Service，E2 实现）                        │
│                                                                  │
│  输入: Agent Artifacts (RiskFinding / EvidencePackage / etc.)    │
│                                                                  │
│  Step 1 — Claim Extraction                                       │
│    从每个 Artifact 中提取所有事实性 Claim                         │
│                                                                  │
│  Step 2 — Citation Verification                                  │
│    对每个 Claim 的每个 citation：                                 │
│      a) 检索引用段落的实际内容（从文档库 / 准则库）                 │
│      b) 使用 LLM 判断引用内容是否支撑 Claim                       │
│      c) 输出支撑/部分支撑/不支撑 判定                             │
│                                                                  │
│  Step 3 — Annotated Reference Comparison                         │
│    将 Agent 的全部引用与 Benchmark 标准引用集合对比               │
│                                                                  │
│  Step 4 — 计算四个指标并生成 GroundingReport                      │
│                                                                  │
│  输出: GroundingReport { citation_precision, citation_recall,    │
│          unsupported_claim_rate, hallucination_rate,              │
│          per_claim_details }                                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Layer 4 — Workflow Evaluation（工作流评估）

### 5.1 概述

Layer 4 是最顶层的评估，衡量**完整审计工作流的端到端表现**——从文档上传到 Review 审批的整个链路。与 L1–L3 不同，L4 不使用自动化的 Benchmark 标注，而是基于**真实审计案例**的执行记录进行评估。

**触发时机：** E4（Audit Services）端到端工作流完成后。

**数据来源：** Audit Log（Append-Only Hash Chain）+ Human Reviewer 反馈记录。

### 5.2 指标体系

| 指标 | 英文名 | 含义 | 计算方式 | 目标值 |
|------|--------|------|----------|--------|
| **Completion Rate** | 工作流完成率 | 启动的工作流中无需人工强制终止即完成的比率 | 成功完成数 / 总启动数 | ≥ 0.90 |
| **Human Intervention Count** | 人工干预次数 | 每个工作流平均触发 HITL（Human-in-the-Loop）的次数 | 总 HITL 触发数 / 总工作流数 | ≤ 2.0 |
| **Time Reduction vs Manual** | 相对人工的时间缩减 | AuditFlow 完成审计相对于纯人工审计的时间缩减比例 | (人工时间 − AuditFlow 时间) / 人工时间 | ≥ 0.60 |

### 5.3 Completion Rate

```
Completion Rate = |{workflow: status == COMPLETED}| / |{所有启动的 workflow}|

不视为"完成"的状态：
  - ABORTED：系统出现不可恢复错误
  - STUCK：超过 max_iterations 或 timeout 仍未产出
  - REJECTED：Human Reviewer 三次退回后仍不达标
```

Completion Rate 是系统可用性的底线指标——如果工作流频繁中断，意味着 Agent 链存在严重的设计缺陷。

### 5.4 Human Intervention Count

```
Human Intervention Count = 所有 workflow 的 HITL 触发总次数 / workflow 总数

HITL 触发场景（E4 定义）：
  1. Planner 产出的 Audit Plan 需要 Human 确认
  2. Risk Agent 置信度 < threshold → 需要 Human 判定
  3. Reviewer 退回上游 → Human 需要介入裁决
  4. 任何 Agent 状态为 NEEDS_HUMAN
```

Human Intervention Count 过高的含义：
- > 3.0：Agent 链过于依赖人工，自动化价值有限
- 1.0–2.0：理想区间——关键决策点有人工介入，但大部分流程自动化
- < 0.5：可能存在合规风险——过于自动化可能遗漏需要人工判断的场景

### 5.5 Time Reduction vs Manual

```
Time Reduction = (ManualBaseline − AuditFlowTime) / ManualBaseline

ManualBaseline: 经验丰富的审计师完成同类案例的平均时间（通过时间研究测定）
AuditFlowTime: 从文档上传到 Reviewer APPROVED 的端到端耗时

目标：≥ 60% 时间缩减。
```

### 5.6 L4 执行机制

L4 不通过 EvaluationRunner 自动执行（因为依赖真实案例和人工评估），而是通过以下机制收集数据：

- **Audit Log 统计：** 每次工作流执行的所有 Event 被记录到 Append-Only Hash Chain（ADR-004），L4 指标通过查询 Audit Log 自动计算。
- **Human Feedback 收集：** 每次 HITL 触发时，Human Reviewer 的决策（APPROVE / REJECT / ESCALATE）被记录，作为 Human Intervention Count 和 Completion Rate 的输入。
- **每周汇总报告：** Cron Job 每周自动生成 L4 Dashboard 报告。

---

## 6. EvaluationRunner 与 Experiment Tracker 接口

### 6.1 EvaluationRunner

`EvaluationRunner` 是 L1–L3 评估的统一执行入口，定义于 E0.5 Milestone 0.5.3（Issue 0.5.3.1）。

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from datetime import datetime
from typing import Any


class Metric(ABC):
    """评估指标的抽象基类。每个指标实现 compute 方法。"""

    name: str
    layer: int  # 1, 2, or 3

    @abstractmethod
    async def compute(
        self,
        prediction: Any,        # AgentResponse 或检索结果
        ground_truth: dict,     # Benchmark Case 的 expected 字段
    ) -> float:
        """计算该指标的分数，返回 0.0–1.0 之间的值。"""
        ...


class EvaluationRunner:
    """统一评估执行器 — 加载 Benchmark，对 Agent/系统执行评估。"""

    def __init__(
        self,
        metrics: list[Metric],
        benchmark_path: str,
        baseline_path: str | None = None,
    ):
        ...

    async def run(
        self,
        target,          # Agent 实例 或 RetrievalSystem 实例
        suite: str,      # Benchmark suite 名称或路径
    ) -> EvaluationReport:
        """执行完整评估流程，返回 EvaluationReport。"""
        ...

    async def run_single_case(
        self,
        target,
        case_id: str,
    ) -> CaseResult:
        """对单个 Benchmark Case 执行评估（用于开发调试）。"""
        ...


class EvaluationReport(BaseModel):
    """评估报告 — Issue 0.5.3.1 定义的输出格式。"""

    agent_name: str                     # 被评估的 Agent 名称
    benchmark_name: str                 # Benchmark suite 名称
    benchmark_version: str              # Benchmark 版本号
    prompt_version: str                 # 使用的 Prompt 版本
    model_name: str                     # 使用的 LLM 模型
    executed_at: datetime               # 执行时间

    metrics: dict[str, float]           # 汇总指标: {"recall@5": 0.87, ...}
    per_case: dict[str, dict[str, float]]  # 逐 Case 明细

    baseline: dict[str, float] | None   # Baseline 分数（如有）
    delta: dict[str, float] | None      # 与 Baseline 的差值

    passed: bool                        # 是否通过门禁
    experiment_id: str                  # 关联的 Experiment ID

    failures: list[str]                 # 未通过阈值的指标列表
    warnings: list[str]                 # 警告信息


class RetrievalReport(BaseModel):
    """L1 专用报告 — 检索系统评估结果。"""

    metrics: dict[str, float]
    per_case: dict[str, dict[str, list[float]]]
    passed: bool
```

### 6.2 Experiment Tracker

`Experiment Tracker` 记录每次评估实验的完整上下文，支持历史对比和趋势分析，定义于 E0.5 Milestone 0.5.3（Issue 0.5.3.4）。

```python
class ExperimentTracker:
    """评估实验追踪器 — 记录每次评估的完整快照。"""

    async def create_experiment(
        self,
        report: EvaluationReport,
        prompt_version: str,
        model_name: str,
        git_commit: str,
        config: dict,
    ) -> Experiment:
        """创建一次实验记录。"""
        ...

    async def get_history(
        self,
        agent_name: str,
        metric: str | None = None,
        limit: int = 20,
    ) -> list[Experiment]:
        """获取某 Agent 的历史实验记录，支持按指标筛选。"""
        ...

    async def compare(
        self,
        experiment_a: str,   # experiment_id
        experiment_b: str,   # experiment_id
    ) -> ComparisonReport:
        """对比两次实验的结果差异。"""
        ...


class Experiment(BaseModel):
    """单次实验记录。"""

    experiment_id: str                  # UUID
    agent_name: str
    benchmark_name: str
    benchmark_version: str

    prompt_version: str                 # 使用的 Prompt 版本号
    model_name: str                     # 使用的 LLM 模型
    git_commit: str                     # 代码版本（Git SHA）
    config: dict                        # 运行配置快照

    metrics: dict[str, float]           # 指标分数
    baseline_metrics: dict[str, float] | None
    delta: dict[str, float] | None

    passed: bool
    executed_at: datetime
    duration_seconds: float
    cost_usd: float                     # LLM 调用总成本

    report_path: str                    # 完整报告持久化路径


class ComparisonReport(BaseModel):
    """两次实验的对比报告。"""

    experiment_a: Experiment
    experiment_b: Experiment
    metric_deltas: dict[str, float]     # 各指标变化量
    winner: str                         # "a" | "b" | "tie"
    summary: str                        # 自然语言总结
```

### 6.3 典型调用流程

```python
# ── 开发者在 Agent 开发完成后运行 ──

# 1. 初始化
runner = EvaluationRunner(
    metrics=[
        RiskClassificationAccuracy(),
        SeverityAccuracy(),
        ReasoningQuality(),
        CitationPrecision(),
        CitationRecall(),
    ],
    benchmark_path="benchmark/",
    baseline_path="results/baseline.json",
)
tracker = ExperimentTracker()

# 2. 执行评估
report = await runner.run(
    target=risk_agent,
    suite="benchmark/",
)

# 3. 记录实验
experiment = await tracker.create_experiment(
    report=report,
    prompt_version="v2",
    model_name="gpt-4-turbo",
    git_commit="abc1234",
    config={"temperature": 0.1, "max_tokens": 4096},
)

# 4. 历史对比
history = await tracker.get_history(agent_name="Risk", metric="risk_classification_accuracy")
comparison = await tracker.compare(history[0].experiment_id, experiment.experiment_id)

# 5. 门禁判断
if not report.passed:
    print(f"❌ PR Blocked: {report.failures}")
else:
    print(f"✅ All gates passed: experiment {experiment.experiment_id}")
```

---

## 7. Baseline 对比与 PR 门禁

### 7.1 Baseline 概念

Baseline 是系统在当前 Prompt 版本 + Model 组合下，在全部 20 个 Benchmark Case 上的**已认证最优分数**。它存储在 `results/baseline.json` 中（受 Git 版本控制），作为后续所有变更的对比基准。

### 7.2 Baseline 建立时机

在 E3 Agent Core Runtime 完成后，对全部 20 个 Case 执行三种模式下的评估，建立 Baseline Score 矩阵：

| 模式 | 说明 | 架构 |
|------|------|------|
| **GPT-4 Direct** | 将文档全文 + 财务数据一次性发送给 GPT-4，要求输出风险分析 | 单次 LLM 调用，无 RAG，无 Agent |
| **Naive RAG** | 文档切块 → Embedding → 向量检索 → LLM 生成 | 基础 RAG，无 Ontology，无 Agent 迭代 |
| **AuditFlow E3** | Planner → Knowledge → Risk → Evidence → Reviewer 完整 Agent 链 | 5 Agent + Ontology + HITL |

### 7.3 门禁规则（Gate Rules）

| 规则 | 条件 | 动作 | 说明 |
|------|------|------|------|
| **质量退化门禁** | 新 Prompt 版本任一 Primary Metric < Baseline × 0.95 | 🚫 **PR Blocked** | 任何主要指标不能低于 Baseline 的 95% |
| **单一指标保护** | 某领域 mean score 下降 > 5% | ⚠️ **Warning + 需团队 Review** | 防止在总分不变的情况下某领域严重退化 |
| **回归检测** | 任意单个 Case score < Baseline − 10pp | 🚫 **PR Blocked** | 百分点级别的退化不可接受 |
| **成本超限** | avg_cost_per_case > Baseline × 1.5 | ⚠️ **Warning** | 成本超出 50% 触发警告 |
| **延迟超限** | p95_latency > Baseline × 2.0 | ⚠️ **Warning** | p95 延迟翻倍触发警告 |

### 7.4 门禁执行流程

```
PR 提交
  │
  ▼
CI Pipeline 触发
  │
  ├── Lint + Type Check（< 2 min）── 失败 → 直接 Block
  │
  ├── Unit Tests（< 5 min）── 失败 → 直接 Block
  │
  ├── L1 Retrieval Eval ───────────────┐
  ├── L2 Agent Eval（per Agent）        ├── 并行执行
  └── L3 Grounding Eval ───────────────┘
       │
       ▼
  生成 EvaluationReport
       │
       ▼
  ┌─────────────────────┐
  │ Score >= Baseline?  │
  └──────────┬──────────┘
        Yes  │  No
         ✅  │  🚫
      Merge  │  Block + 生成 Report
             │  Report 附带:
             │    - 退化的指标和幅度
             │    - 受影响的 Case 列表
             │    - 建议的修复方向
```

### 7.5 Baseline 文件结构

```json
{
  "version": "1.0",
  "prompt_version": "v1.0.0",
  "model": "gpt-4-turbo",
  "date": "2026-03-15",
  "scores": {
    "L1_retrieval": {
      "recall_at_5": 0.87,
      "recall_at_20": 0.96,
      "mrr": 0.72,
      "ndcg_at_10": 0.78
    },
    "L2_agent": {
      "planner": {
        "plan_completeness": 0.82,
        "ontology_alignment": 0.78
      },
      "knowledge": {
        "precision_at_5": 0.74,
        "citation_accuracy": 0.88
      },
      "risk": {
        "risk_classification_accuracy": 0.82,
        "severity_accuracy": 0.78,
        "reasoning_quality": 4.2
      },
      "evidence": {
        "evidence_coverage": 0.76,
        "citation_source_accuracy": 0.83
      },
      "reviewer": {
        "issue_detection_rate": 0.85,
        "false_positive_rate": 0.12
      }
    },
    "L3_grounding": {
      "citation_precision": 0.85,
      "citation_recall": 0.80,
      "unsupported_claim_rate": 0.08,
      "hallucination_rate": 0.03
    }
  },
  "per_domain": {
    "revenue_recognition":  { "risk_classification_accuracy": 0.85, "severity_accuracy": 0.80 },
    "ar_impairment":        { "risk_classification_accuracy": 0.80, "severity_accuracy": 0.75 },
    "inventory_valuation":  { "risk_classification_accuracy": 0.78, "severity_accuracy": 0.73 },
    "expense_cutoff":       { "risk_classification_accuracy": 0.83, "severity_accuracy": 0.80 },
    "fixed_asset":          { "risk_classification_accuracy": 0.81, "severity_accuracy": 0.77 },
    "control_testing":      { "risk_classification_accuracy": 0.84, "severity_accuracy": 0.82 },
    "fraud_risk":           { "risk_classification_accuracy": 0.80, "severity_accuracy": 0.76 }
  },
  "cost_profile": {
    "mean_cost_per_case": 0.45,
    "p95_latency_seconds": 22.3
  }
}
```

### 7.6 Baseline 更新策略

Baseline **只能向上更新**——新版本的分数必须在所有维度上 ≥ 当前 Baseline 才能成为新 Baseline。

| 场景 | 操作 |
|------|------|
| 新版本所有指标 ≥ Baseline | ✅ 自动更新 Baseline 为新版本分数 |
| 新版本部分指标 ≥ Baseline，部分指标轻微下降（< 5%）但通过门禁 | ⚠️ 手动 Review 后由团队决定是否更新 |
| 新版本任一指标 < Baseline × 0.95 | 🚫 PR Blocked，不可合并 |
| 新增 Benchmark Case | 新 Case 的分数独立记录，不影响已有 Baseline |
| Model 升级（如 GPT-4 → GPT-4-turbo → GPT-5） | 新建 Baseline 文件，旧 Baseline 归档保留 |

---

> **关联文档：**
> - [Benchmark Dataset 规范](./benchmark.md) — E7 Benchmark 数据结构
> - [Agent Contract v1.0](../api/agent-contract.md) — Agent 输入输出规范
> - [Artifact Schema](../api/artifact-schema.md) — Artifact 类型定义
> - [ADR-004 Audit Log](../architecture/ADR-004-Audit-Log.md) — L4 数据来源
