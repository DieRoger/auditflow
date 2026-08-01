# Related Work — Research Positioning

AuditFlow 的技术路线对应四个成熟研究方向。本文档为论文写作和申请材料提供
文献锚点（每个方向给出核心论文、与 AuditFlow 的对应关系、差异点）。

---

## 1. RAG / Evidence Grounding

**核心文献:**
- Lewis et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive
  NLP Tasks*. NeurIPS. — RAG 奠基论文
- Guu et al. (2020). *REALM: Retrieval-Augmented Language Model Pre-Training*.
  ICML.
- Shuster et al. (2021). *Retrieval Augmentation Reduces Hallucination in
  Conversation*. EMNLP.

**AuditFlow 对应:**
- 67 PDFs (ISA/CAS/IAASB) → chunk → BGE embedding → PGVector → hybrid search
- Citation 必须来自检索结果（`document_id="llm_analysis"` bug 修复是分水岭）

**差异点（AuditFlow 贡献）:**
- 审计领域要求 **citation 可审计**：不仅引用存在，还要 page/chunk 可追溯
- Evidence Graph 将"检索相关"升级为"断言级充分性判定"（CUTOFF→[INVOICE,DELIVERY]）

---

## 2. Agent / LLM Evaluation

**核心文献:**
- Chang et al. (2023). *A Survey on Evaluation of Large Language Models*. 
- Liu et al. (2023). *AgentBench: Evaluating LLMs as Agents*. ICLR 2024.
- Wang et al. (2024). *A Survey on LLM-based Autonomous Agents*.

**AuditFlow 对应:**
- L1-L4 四层评估体系（Detection/Assessment/Procedure/Workflow）
- 每层独立 Ground Truth（Abnormal_Label / Risk_Class / Rule Mapping / Required Fields）

**差异点（AuditFlow 贡献）:**
- 大多数 Agent 评估停留在单指标（success rate）；AuditFlow 强调
  **层级化 Ground Truth** + **Balanced Accuracy**（处理类别不平衡）+ **Error Analysis**
- Review Reduction (89%) 是审计特有的"人工效率"指标，主流 Agent 评测不覆盖

---

## 3. Human-in-the-loop AI

**核心文献:**
- Lipton (2018). *The Mythos of Model Interpretability*. ACM Queue. —
  可解释性与"建议 vs 决策"的区分
- Amershi et al. (2019). *Guidelines for Human-AI Interaction*. CHI.
- Mosqueira-Rey et al. (2023). *Human-in-the-loop machine learning: a state
  of the art*. AI Review.

**AuditFlow 对应:**
- ReviewQueue 三态（ACCEPT / DISMISS / NEED_MORE_EVIDENCE）—— 不是 Approve/Reject
- 设计原则: *AI recommendation ≠ AI decision*；Assessment 是"推荐"不是"判定"
- Accepted Finding Rate 作为 HITL 质量指标

**差异点（AuditFlow 贡献）:**
- 审计领域的 HITL 特殊性：**NEED_MORE_EVIDENCE**（证据不足而非风险不存在）
  是审计中最常见的中间态，通用 HITL 文献少有覆盖
- Evidence Graph 与 HITL 联动：证据缺失 → 队列暂停 → 补充证据 → 重新审

---

## 4. AI for Auditing

**核心文献方向:**
- Appelbaum et al. (2017). *Artificial intelligence in accounting and auditing*.
  Journal of Emerging Technologies in Accounting.
- No & Vasarhelyi (2017). *Continuous auditing*. 
- Bao et al. (2020). *Detecting accounting fraud with machine learning*.
- Perols et al. (2017). *Machine learning in fraud detection*.

**AuditFlow 对应:**
- 12 Signal Detectors → Risk Scoring（规则驱动，可解释）
- ISA 520 分析程序（Ratio/Trend）、ISA 320 Materiality、ISA 500 Evidence
- Error Analysis 中的 FN 类型（Split/Round-Trip）直接对应文献中的舞弊模式

**差异点（AuditFlow 贡献）:**
- 从"fraud detection 算法"走向"完整审计执行管线"
  （风险评估 → 程序 → 证据 → 错报 → 意见），
  且严格区分 **检测能力** 与 **审计判断能力** 的边界（Error Analysis §4）

---

## 研究定位一句话

> AuditFlow 将 RAG 的证据基础、分层 Agent 评估、审计特定的 HITL 中间态，
> 与规则驱动的可解释异常检测结合，构成一个 **Evidence-driven AI Audit Copilot**；
> 其核心方法论贡献是"四层 Ground Truth 评估 + 诚实的 Error Analysis"，
> 而非任何单一算法的精度提升。
