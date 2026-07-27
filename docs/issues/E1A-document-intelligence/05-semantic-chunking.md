# 1A.2.2 — Semantic Chunking
- **Epic:** E1A Document Intelligence
- **Labels:** `chunking`, `document`, `phase-1a`
- **Depends on:** 1A.2.1 (Layout Analysis + Table Extraction)

## 描述

将版面分析后的文档按语义边界切分为 Chunk，为后续 Embedding 和 Vector 检索做准备。切分策略以 Section/Paragraph/Table 为自然边界，保证每个 Chunk 语义完整、上下文自包含，避免在句子中间切断。

区别于简单的固定长度滑动窗口切分，Semantic Chunking 遵循以下优先级：
1. **一级 Section 边界**（最大的 H1 标题）强制切分
2. **二级 Section 边界**（H2 标题）优先切分
3. **段落边界**（连续 Paragraph block 归为一个 Chunk）
4. **表格独立成 Chunk**（每个 TableData 单独为一个 Chunk，附带 caption）
5. 若上述切分后仍超过 `max_chunk_size=1024` tokens，在段落内按句子边界切分

每个 Chunk 携带上下文元数据（所属 section 路径、前后 Chunk ID），供检索时召回相邻上下文。

## Acceptance Criteria

- [ ] 按 Section → Paragraph → Table 语义边界切分，不在句子中间切断
- [ ] 每个 Chunk 含 `chunk_index` / `section_path` / `prev_chunk_id` / `next_chunk_id`
- [ ] 表格 Chunk 保留 Markdown Table 表示（LLM 友好）
- [ ] `max_chunk_size=1024` tokens（tiktoken cl100k_base 估算），允许 ±10% 容差
- [ ] 单段落超过 max_chunk_size 时按句子边界递归切分
- [ ] Chunk 内容自包含：若段落含代词（"该公司"/"上述"），在 Chunk 开头注入上下文前缀（section title）
- [ ] 输出 `list[DocumentChunk]`，可直接喂入 EmbeddingProvider
- [ ] Chunk 元数据含 `source_type=CLIENT_DOCUMENT`，为 PGVector Pipeline 做准备

## I/O 接口

```python
class DocumentChunk(BaseModel):
    """一个语义完整的文档切片"""
    chunk_id: str                           # 全局唯一 chunk ID
    document_id: str
    chunk_index: int                        # 在文档中的序号（从 0 开始）
    content: str                            # Chunk 文本（自包含，≤ 1024 tokens）
    content_type: Literal["TEXT", "TABLE"]  # 内容类型
    section_path: list[str]                 # 层级标题路径，如 ["财务报表", "资产负债表", "流动资产"]
    page_range: tuple[int, int]             # (start_page, end_page) 1-based
    table_id: str | None                    # 若 content_type=TABLE，关联 TableData.table_id
    prev_chunk_id: str | None
    next_chunk_id: str | None
    token_count: int                        # tiktoken 估算的 token 数
    metadata: dict[str, Any]                # 扩展字段（embedding 生成后注入）

class SemanticChunker(ABC):
    """语义切分器抽象"""
    async def chunk(
        self,
        layout_result: LayoutAnalysisResult,
        document_id: str,
        max_chunk_tokens: int = 1024,
    ) -> list[DocumentChunk]:
        ...
```
