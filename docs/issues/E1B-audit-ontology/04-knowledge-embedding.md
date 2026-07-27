# 1B.2.2 — Knowledge Embedding & Indexing

- **Epic:** E1B — Audit Intelligence Model
- **Labels:** `knowledge`, `embedding`, `pgvector`
- **Depends on:** 1B.2.1 (审计准则导入), 0.3.2 (Embedding Service + VectorStore)
- **Estimate:** —

## Description

将 1B.2.1 导入的审计准则 Chunk 通过 Embedding Provider 向量化后写入 PGVector（`source_type=AUDIT_STANDARD`），使 Knowledge Agent 能够通过语义检索查找相关准则条款。同时建立准则之间的交叉引用索引（如 ISA 315 引用 ISA 240），支持 Cross-Reference 扩展查询。

## Acceptance Criteria

- [ ] 所有 5 部准则的 Chunk 完成 Embedding 并写入 PGVector
- [ ] `source_type=AUDIT_STANDARD` 过滤正常工作
- [ ] 按 `standard_id` 过滤：如仅检索 ISA 240 相关内容
- [ ] 按 `topic` / `section` 元数据过滤
- [ ] 交叉引用索引：给定一个准则条款 → 返回其引用/被引用的其他条款

```sql
-- 交叉引用表
CREATE TABLE standard_cross_reference (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_standard_id VARCHAR NOT NULL,   -- 引用方
    source_paragraph VARCHAR NOT NULL,
    target_standard_id VARCHAR NOT NULL,   -- 被引用方
    target_paragraph VARCHAR,
    reference_type VARCHAR,                -- normative | informative
    context TEXT                           -- 引用上下文
);
```

- [ ] Embedding 批量处理：支持分批写入，避免 OOM
- [ ] 幂等性：重复执行不产生重复向量（按 `(standard_id, paragraph)` 去重，或先删后插）
- [ ] L1 Evaluation 就绪：`source_type=AUDIT_STANDARD` 的检索可纳入 Recall@K / MRR 评估

## I/O Interface

```python
# 利用 0.3.2 已定义的 VectorStore 接口
class VectorStore(ABC):
    async def insert(self, items: list[EmbeddingItem]) -> None: ...
    async def search(
        self, query_vector: list[float], top_k: int,
        filters: dict  # {"source_type": "AUDIT_STANDARD", "standard_id": "ISA-240"}
    ) -> list[EmbeddingItem]: ...

# EmbeddingItem 示例
EmbeddingItem(
    id="isa315-para27",
    firm_id="*",                   # 准则对所有事务所通用
    client_id="*",
    engagement_id="*",
    source_type="AUDIT_STANDARD",
    source_id="ISA-315-¶27",
    content="The auditor shall design and perform risk assessment procedures...",
    embedding=[0.023, -0.154, ...],
    metadata={
        "standard_id": "ISA-315",
        "paragraph": "¶27",
        "section": "Risk Assessment Procedures",
        "topic": "inherent_risk",
        "standard_body": "IAASB",
        "hierarchy_path": "ISA 315 > Part 4 > Identifying RMM > ¶27"
    },
    security_level="PUBLIC",
    created_at=...
)
```

## Related ADR

- [ADR-002 — 审计本体模型](../architecture/ADR-002-Ontology-Model.md)（§6.1：向量检索与本体查询互补）
- [ADR-003 — Vector Schema](../architecture/ADR-003-Vector-Schema.md)
