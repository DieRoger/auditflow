# 02 — Document Pipeline Validation

**父 Issue：** E3.5 System Bring-up
**优先级：** P0
**预计工作量：** 1-2 天

## 当前状态

以下组件各有独立实现：

| 组件 | 代码位置 | 独立测试 |
|------|---------|---------|
| Upload API | `api/routers/documents.py` | `test_document_api.py` |
| PDF Parser | `infrastructure/parser/pdf_parser.py` | `test_pdf_parser.py` |
| OCR Service | `infrastructure/ocr/ocr_service.py` | `test_ocr_service.py` |
| Layout Analysis | `infrastructure/parser/layout.py` | `test_layout.py` |
| Embedding | `infrastructure/vector/openai_embedding.py` | ❌ 无 |
| PGVector Store | `infrastructure/vector/pgvector_store.py` | ❌ 无 |

**问题：** 没有一个脚本或测试验证从"上传 PDF"到"数据库有 chunk + embedding"的完整链路。

## 目标

验证全链路可运行：

```
PDF 文件
  → Upload API (POST /documents/upload)
  → PDF Parser（提取文本 + 表格）
  → OCR Service（处理扫描页）
  → Layout Analysis（识别段落/表格边界）
  → Semantic Chunking（语义切分）
  → OpenAI Embedding（向量化）
  → PGVector Store（存储 chunk + embedding）
  → 查询验证：SELECT * FROM chunks WHERE document_id = ?
```

## 验收标准

### 必须通过

1. **Upload 成功。** `POST /documents/upload` 返回 200，document_id 有效。
2. **Chunk 可查。** `SELECT COUNT(*) FROM chunks WHERE document_id = ?` 返回 > 0。
3. **Embedding 非空。** 随机抽取一个 chunk，其 `embedding` 字段不为 NULL 且维度正确。
4. **Metadata 完整。** Chunk 包含 `page_number`、`chunk_index`、`token_count` 等元数据。

### 应该通过

5. **Vector Search 可召回。** 对文档内容提问，`vector_search` 返回相关 chunk。
6. **OCR 覆盖扫描页。** 对扫描件 PDF，OCR 后的文本与原生文本页正确合并。

## 产出物

1. `scripts/validate_pipeline.py` — 端到端验证脚本（上传 → 等待处理 → 查询验证）
2. `tests/integration/test_document_pipeline.py` — 集成测试
3. 如发现链路断裂，修复最小的集成问题（不重写组件）

## 不做的事

- 不优化 Chunking 策略
- 不调整 Embedding 模型
- 不新增 Parser 功能
