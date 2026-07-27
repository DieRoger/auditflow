# 1B.2.1 — 审计准则导入

- **Epic:** E1B — Audit Intelligence Model
- **Labels:** `knowledge`, `ingestion`, `standards`
- **Depends on:** 0.3.2 (Embedding Service + VectorStore)
- **Estimate:** —

## Description

将核心审计准则和会计准则的结构化文本导入系统知识库，作为 Knowledge Agent 检索的权威语料。MVP 范围涵盖 ISA 315（风险识别与评估）、ISA 330（审计应对）、ISA 500（审计证据）、ISA 240（舞弊责任）以及 IFRS 15（客户合同收入）。

导入流程：原始准则文本 → 按段落/条款 Chunking → 存储为结构化文档（含标准编号、条款号、层级路径等元数据）→ 后续由 1B.2.2 进行 Embedding。

## Acceptance Criteria

- [ ] ISA 315 (Revised 2019) 全文导入，按段落分块，含条款号元数据
- [ ] ISA 330 全文导入，按段落分块，含条款号元数据
- [ ] ISA 500 全文导入，按段落分块，含条款号元数据
- [ ] ISA 240 全文导入，按段落分块，含条款号元数据
- [ ] IFRS 15 全文导入，按段落分块，含条款号元数据
- [ ] 每个 Chunk 携带结构化元数据：

```json
{
  "standard_id": "ISA-315",
  "standard_name": "ISA 315 (Revised 2019)",
  "standard_body": "IAASB",
  "paragraph": "¶27",
  "section": "Risk Assessment Procedures",
  "topic": "inherent_risk",
  "hierarchy_path": "ISA 315 > Part 4 > Identifying RMM > ¶27"
}
```

- [ ] 准则文本以 `source_type=AUDIT_STANDARD` 存储，`security_level=PUBLIC`
- [ ] 导入脚本幂等：重复运行不产生重复记录（按 `(standard_id, paragraph)` 去重）
- [ ] 支持增量更新：新修订准则可通过相同脚本追加导入

## I/O Interface

```python
# 准则文档的存储模型（导入后写入 document 表或直接作为 knowledge_chunk）
class StandardChunk(BaseModel):
    id: str
    standard_id: str            # "ISA-315" | "ISA-330" | "ISA-500" | "ISA-240" | "IFRS-15"
    standard_name: str          # 人类可读全称
    standard_body: str          # "IAASB" | "IFRS Foundation"
    paragraph: str              # 条款号，如 "¶27"、"¶A42"
    section: str | None         # 所属章节
    content: str                # 条款原文
    hierarchy_path: str         # 层级路径，用于上下文导航
    language: str               # "en" （MVP 仅英文）
    metadata: dict

# 导入脚本接口
# python -m auditflow.tools.import_standards \
#     --standards ISA-315,ISA-330,ISA-500,ISA-240,IFRS-15 \
#     --source-dir data/standards/ \
#     --db-url postgresql://...
```

## Related ADR

- [ADR-002 — 审计本体模型：Graph-Ready PostgreSQL Schema](../architecture/ADR-002-Ontology-Model.md)（§2.3 Standard 节点类型，通过 REFERENCES 边与推理链关联）
