# 0.3.2 — Embedding Service + VectorStore

- **Epic:** E0 — Foundation
- **Labels:** `ai-infra`, `phase-0`
- **Depends on:** 0.1.2
- **Estimate:** —

## Description
实现 Embedding Provider 抽象层和 VectorStore 接口（基于 PGVector HNSW 索引）。EmbeddingItem 包含完整的审计上下文字段（firm_id / client_id / engagement_id / source_type / security_level），VectorStore 支持按这些维度过滤检索。

## Acceptance Criteria
- [ ] PGVector HNSW 索引
- [ ] 支持 firm_id 过滤
- [ ] 支持 engagement_id 过滤
- [ ] 支持 source_type 过滤
- [ ] 支持 security_level 过滤

## I/O Interface
```python
class EmbeddingProvider(ABC):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    def dimension(self) -> int: ...

class EmbeddingItem(BaseModel):
    id: str
    firm_id: str              # 审计事务所
    client_id: str            # 被审计客户
    engagement_id: str        # 审计年度
    source_type: Literal["CLIENT_DOCUMENT","AUDIT_STANDARD","WORKPAPER","RISK_CASE"]
    source_id: str
    content: str
    embedding: list[float]
    metadata: dict
    security_level: str       # PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED
    created_at: datetime

class VectorStore(ABC):
    async def insert(self, items) -> None: ...
    async def search(self, query_vector, top_k, filters) -> list[EmbeddingItem]: ...
```
