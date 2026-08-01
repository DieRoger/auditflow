# Error Analysis — Kaggle Vertical Slice

系统性的错误分析：为什么会错、错在哪里、如何改进。

**数据:** Kaggle #1, 7000 rows, Threshold=15
**FP (误报):** 251 | **FN (漏报):** 437

---

## 1. Detection — False Positives (为什么误报)

FP 总数: **251**，其中触发最多的信号:

| Signal | FP 中出现次数 | 说明 |
|--------|--------------|------|
| audit_violation | 251 | 规则违规计数 — 违规≠舞弊 |
| province_mismatch | 233 | 跨省交易 — 正常业务常见 |
| duplicate_invoice | 200 | 发票重复 — 可能是系统重试 |
| night | 87 | 夜间交易 — 业务高频特征 |
| weekend | 82 | 周末交易 — 业务高频特征 |
| threshold_violation | 41 | 阈值违规 — 规则严格但业务允许 |
| temporal_burst | 40 | 时序爆发 — 可能是月末效应 |
| amount_spike | 33 | 金额异常 — 相对可靠 |
| tax_mismatch | 29 | 税号不匹配 — 供应商信息滞后 |
| related_party | 5 | 关联方 — 可靠信号 |

FP 交易特征: 平均金额 $48,192 (全量平均 $50,124)

| 特征 | FP 中占比 | 说明 |
|------|----------|------|
| Night_Transaction | 35% | 夜间交易是业务特征，不是舞弊特征 |
| Weekend_Flag | 33% | 同上 |
| Province_Mismatch | 93% | 跨省交易普遍存在 |
| Audit_Rule_Violation | 100% | 规则违规 ≠ 舞弊 |
| Temporal_Burst | 16% | 时序爆发可能是正常月末效应 |
| Amount_Spike | 29% | 金额异常相对可靠 |

### FP 根因

1. **规则特征与业务特征重叠**: night/weekend/province 在真实业务中高频出现，
   这些信号触发≠舞弊。当前 `night` 保留为 score 信号（weight 0.5），贡献了主要 FP。
2. **阈值标定**: threshold=15 是在 F1 优化下选择的，偏保守（宁可误报不漏报）。

### 改进方向

- 将 `night` 完全降级为 info 信号（Precision 15.8%），预计 FP 显著下降
- 引入金额感知：小金额夜间交易不触发（金额 × 信号置信度 加权）
- 组合信号：仅当 2+ 独立信号同时触发才升 HIGH

---

## 2. Detection — False Negatives (为什么漏报)

FN 总数: **437**，平均得分 4.6 (max 14.0，threshold=15)

### 漏报的异常类型分布

| Abnormal Type | FN 数量 | |
|---------------|--------|--|
| High_Risk_Vendor | 134 | |
| Cross_Province_Mismatch | 112 | |
| Temporal_Burst | 82 | |
| Tax_ID_Mismatch | 61 | |
| Split_Transaction | 48 | |

### 漏报交易特征

- 平均金额: $36,928 (全量 $50,124) — **金额小更容易漏**
- 未触发任何 score 信号的 FN 比例较高（信号未覆盖的异常类型）

### FN 根因

1. **信号未覆盖**: `Split_Transaction`、`Round_Trip_Transfer` 等异常类型没有对应信号。
2. **小金额异常**: 金额阈值信号（amount_spike）对低基数交易不敏感。
3. **评分天花板**: 单信号 LOW severity × weight 无法达到 threshold=15。

### 改进方向

- 新增 Split_Transaction 信号（同源多笔小额拆分）
- 新增 Round_Trip 信号（A→B→A 资金回流）
- 对低金额交易使用更低 threshold 的次级规则

---

## 3. Assessment — MEDIUM 系统性偏向 HIGH

| GT | Pred LOW | Pred MEDIUM | Pred HIGH | Accuracy |
|----|----------|-------------|-----------|----------|
| LOW (6045) | 5300 | 494 | 251 | 87.7% |
| MEDIUM (875) | 239 | 177 | 459 | 20.2% |
| HIGH (80) | 15 | 6 | 59 | 73.8% |

### 根因

MEDIUM 是 Risk_Class=1 的中间档，但 Kaggle 的 Risk_Class 标注粒度与我们的
score→severity 映射（score≥15=HIGH, 5-15=MEDIUM）不一致：
Kaggle 的 Risk_Class=1 异常检测分数普遍 ≥15（因为检测分数反映异常强度而非风险等级）。

### 改进方向

- 用 Risk_Class 分布重新标定 score→level 阈值（例如 score≥20 才判 HIGH）
- 或引入 per-class 权重优化 Balanced Accuracy

---

## 4. 总结：当前系统能力的真实边界

| 能力 | 真实边界 |
|------|----------|
| 找出值得复核的交易 | ✅ Review Reduction 89% |
| 判断风险等级排序 | ⚠️ 相邻准确率 96.2%，但 MEDIUM/HIGH 分界偏 |
| 判断具体舞弊类型 | ❌ 信号未覆盖 Split/Round-Trip 等类型 |
| 给出程序建议 | ✅ Mapping 100%（但未验证正确性） |
| 证据引用完整性 | ✅ 100% |
| 证明审计意见正确 | ❌ 无此能力，也不应该宣称 |

这份分析明确了：AuditFlow 是 **Copilot**（帮审计师缩小范围、提供证据），
不是 **Auditor**（判定对错）。

---

## 5. Future Work — 研究路线图

| Current Limitation | Root Cause | Future Direction |
|--------------------|-----------|------------------|
| `High_Risk_Vendor` FN (134) | 无供应商风险评估维度 | 供应商知识图谱 (vendor graph + risk score) |
| `Split_Transaction` FN (48) | 无序列检测器 | Sequence Pattern Mining (同源多笔拆分检测) |
| `Round_Trip_Transfer` FN (107) | 无图搜索能力 | Neo4j 图遍历 (A→B→A 资金回流) |
| MEDIUM/HIGH 分界偏 | score→level 标定与 GT 粒度不一致 | 用 Risk_Class 分布重新标定 + per-class 优化 |
| FP 中 `night` 贡献 35% | night 保留为 score 信号 | 降级为 info + 金额感知加权 |
| FP 中 `duplicate_invoice` 80% | 发票重试≠舞弊 | 引入时间窗 (重试 <24h 不算异常) |
| Evidence 只有引用完整性 | Kaggle 无 PDF 实体 | 在真实文档数据集上验证证据真实性 |
| Procedure 只验证 Mapping | 无事务所程序基线 | 邀请领域专家标注程序选择 (human baseline) |

> 以上每一项都是独立的可发表子课题。优先级建议: 供应商知识图谱 → 图遍历 (Neo4j) → 专家基线。
