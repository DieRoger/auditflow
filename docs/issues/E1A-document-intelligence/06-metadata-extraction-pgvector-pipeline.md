# 1A.2.3 — Metadata Extraction + PGVector Pipeline
- **Epic:** E1A Document Intelligence
- **Labels:** `metadata`, `pipeline`, `pgvector`, `phase-1a`
- **Depends on:** 1A.2.2 (Semantic Chunking), 0.3.2 (Embedding Service + VectorStore)

## 描述

实现文档元数据提取与 PGVector 写入 Pipeline。这是 Document Intelligence 管道的最后一环，将语义切分后的 Chunk 转化为 `EmbeddingItem`（source_type=CLIENT_DOCUMENT），调用 EmbeddingProvider 生成向量，批量写入 PGVector VectorStore，使文档内容可被 E2 Retrieval Engine 检索。

**元数据提取**：从 `ParsedDocument` 和 `LayoutAnalysisResult` 中自动提取文档级元数据 — 公司名称、财报年度、报表类型（年报/半年报/季报）、会计准则（IFRS/CAS）、审计机构等。优先使用规则匹配（正则/关键词），辅助 LLM 分类（仅对关键字段兜底）。

**Pipeline 职责**：编排 Chunk → EmbeddingItem 转换 → Embedding 批量生成 → VectorStore.insert_batch()，全程记录 trace_id，失败 Chunk 标记后继续不阻塞。

## Acceptance Criteria

- [ ] 规则引擎提取 ≥ 5 类元数据字段（company_name / report_year / report_type / accounting_standard / auditor）
- [ ] 元数据存储到 documents 表的 metadata JSONB 字段
- [ ] Pipeline 输入 `list[DocumentChunk]` → 输出写入 PGVector 的 `EmbeddingItem` 列表
- [ ] 每个 Chunk 调用 `EmbeddingProvider.embed_single()` 生成向量（维度由 Provider 决定：OpenAI 3072 或 BGE-M3 1024）
- [ ] 向量通过 `VectorStore.insert_batch()` 批量写入（每批 ≤ 100 条，避免 PG 事务过大）
- [ ] `EmbeddingItem.source_type` = `CLIENT_DOCUMENT`
- [ ] `EmbeddingItem.metadata` 含 `chunk_index` / `section_path` / `content_type` / `page_range`（从 DocumentChunk 携带）
- [ ] 隔离字段 (`firm_id` / `client_id` / `engagement_id` / `security_level`) 全部正确注入
- [ ] Pipeline 执行进度通过 WebSocket 推送（step: `EMBEDDING`）
- [ ] 失败 Chunk 记录错误日志，更新 documents.status 为 `FAILED`（附带 error_message）
- [ ] 全部 Chunk 成功写入后，documents.status → `READY`

## I/O 接口

```python
class DocumentMetadata(BaseModel):
    """文档级自动提取元数据"""
    company_name: str | None               # 公司名称
    report_year: int | None                # 财报年度
    report_type: Literal["ANNUAL", "SEMI_ANNUAL", "QUARTERLY", "UNKNOWN"] | None
    accounting_standard: Literal["IFRS", "CAS", "US_GAAP", "UNKNOWN"] | None
    auditor: str | None                    # 审计机构名称
    currency: str | None                   # 记账本位币
    extracted_at: datetime                 # 提取时间

class DocumentToVectorPipeline(ABC):
    """文档 → PGVector 管道抽象"""

    async def extract_metadata(
        self,
        parsed_doc: ParsedDocument,
        layout_result: LayoutAnalysisResult,
    ) -> DocumentMetadata:
        """从解析结果中提取文档级元数据。"""
        ...

    async def embed_and_index(
        self,
        chunks: list[DocumentChunk],
        document_id: str,
        metadata: DocumentMetadata,
        firm_id: str,
        client_id: str,
        engagement_id: str,
    ) -> list[str]:
        """将 Chunk 列表转化为 EmbeddingItem 并写入 PGVector。

        Returns:
            写入成功的 EmbeddingItem.id 列表。
        """
        ...

# Celery Task 链（在 1A.1.1 中编排）
# Parse → OCR → Layout → Chunk → Metadata + Embed → READY
chain(
    parse.s(document_id),
    ocr.s(),
    layout.s(),
    chunk.s(),
    metadata_extract.s() | embed_and_index.s(),
)
```
