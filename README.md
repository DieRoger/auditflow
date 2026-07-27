# AuditFlow

> **AI-Native Audit Intelligence Platform** — 从 PDF 到审计报告的全自动管线

AuditFlow 是一个端到端的 AI 审计系统，能够自动完成从文档上传到审计报告生成的完整闭环。系统集成了 RAG 检索、多 Agent 协作、证据溯源、审计工作底稿生成等核心能力。

---

## 架构

```
                          ┌─────────────────────┐
  PDF Upload ────────────►│  Document Pipeline   │
                          │  Parse → Chunk → Emb │
                          └─────────┬───────────┘
                                    │ chunks
                                    ▼
                          ┌─────────────────────┐
                          │    Workflow Engine   │
                          │  ┌─────────────────┐│
                          │  │   Planner Agent  ││
                          │  │   Knowledge Agent││
                          │  │    Risk Agent    ││
                          │  │  Evidence Agent  ││
                          │  │  Reviewer Agent  ││
                          │  └─────────────────┘│
                          └─────────┬───────────┘
                                    │
                          ┌─────────▼───────────┐
                          │  Service Layer       │
                          │  Workpaper Generator │
                          │  Report Generator    │
                          └─────────┬───────────┘
                                    │
                          ┌─────────▼───────────┐
                          │   Audit Report       │
                          │   (Markdown/PDF)     │
                          └─────────────────────┘
```

## 特性

- **📄 文档解析** — 支持 Digital PDF（PyMuPDF）和 Scanned PDF（RapidOCR 中文识别）
- **🔍 智能检索** — PGVector 向量检索 + BGE 本地 Embedding（384维，零 API 成本）
- **🤖 5 个审计 Agent** — Planner → Knowledge → Risk → Evidence → Reviewer，全由 LLM 驱动
- **📋 证据溯源** — 每条风险判断可追溯到原始文档的页码和段落
- **📊 工作底稿生成** — 符合审计准则的结构化底稿
- **📝 审计报告生成** — ISA 700 标准格式审计报告
- **📈 评估体系** — 人工标注 + 一致性测试 + Citation 验证
- **🐳 Docker 一键部署** — PostgreSQL+PGVector + MinIO + Redis

## 快速开始

### 前置要求

- Python 3.11+
- Docker Desktop（可选，用于 PostgreSQL+PGVector）
- DeepSeek API Key（[申请](https://platform.deepseek.com/)）

### 安装

```bash
git clone https://github.com/YOUR_USERNAME/auditflow.git
cd auditflow

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY

# 安装 Python 依赖
cd backend
pip install -e .  # 或 pip install -r requirements.txt
```

### 运行

```bash
# 方式 1: 启动全栈（推荐）
docker compose up postgres minio redis -d
cd backend && DATABASE_URL=postgresql+asyncpg://auditflow:auditflow@localhost:5432/auditflow \
  uvicorn src.main:app --port 8000
cd frontend && npm run dev

# 方式 2: 仅运行演示脚本
cd backend
export PYTHONPATH=src
python scripts/full_demo.py          # 端到端：PDF → 审计报告
python scripts/bringup.py            # Workflow 管线验证
python scripts/sprint1_demo.py       # 真实 PDF 检索 + Agent 管线

# 方式 3: 运行评估
python scripts/eval_v2.py            # Baseline 评估
python scripts/eval_v2.py --consistency  # 一致性测试
python scripts/human_eval.py         # 人工标注评估（10 个 Case）
```

### 索引知识库

```bash
# 批量索引 datasets/ 下的 PDF 到 PGVector
python scripts/batch_index.py

# 验证检索
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from infrastructure.vector.pgvector_store import PGVectorStore
from infrastructure.vector.local_embedding import LocalEmbeddingProvider

async def test():
    vec = await LocalEmbeddingProvider().embed(['收入确认风险'])
    engine = create_async_engine('postgresql+asyncpg://auditflow:auditflow@localhost:5432/auditflow')
    async with engine.connect() as conn:
        results = await PGVectorStore(conn).search(vec[0], top_k=3)
        for r in results:
            print(f'p{r.metadata.get(\"page\",\"?\")}: {r.content[:80]}')
    await engine.dispose()

asyncio.run(test())
"
```

## 项目结构

```
auditflow/
├── backend/
│   ├── src/
│   │   ├── agents/          # 5 个 LLM Agent 实现
│   │   │   ├── planner/     # 审计任务拆解
│   │   │   ├── knowledge/   # 准则检索（基于 RAG）
│   │   │   ├── risk/        # 风险识别（基于检索证据）
│   │   │   ├── evidence/    # 证据匹配
│   │   │   └── reviewer/    # 质量审查
│   │   ├── workflows/       # Workflow Engine + HITL + Trace
│   │   ├── infrastructure/  # LLM/OCR/Vector/Parser
│   │   ├── evaluation/      # 评估框架（Metrics/Runner）
│   │   ├── services/        # 底稿生成/报告生成
│   │   └── api/             # FastAPI 路由
│   ├── scripts/             # 演示/评估/工具脚本
│   └── tests/               # 单元/集成测试
├── frontend/                # React + Vite 前端
├── datasets/                # 知识库 PDF
├── docs/issues/             # 架构文档 / ADR
└── docker-compose.yml
```

## 评估结果

| 指标 | 分数 | 说明 |
|------|------|------|
| Risk Classification | 35% | 宽松匹配（substring） |
| Severity Agreement | 80% | 严重性判断准确率 |
| Evidence Recall | 78% | 关键证据关键词覆盖 |
| Severity Consistency | 100% | 同 Case 两次判定一致 |
| Risk Consistency | 75% | 同 Case 风险名称一致 |
| Citation Validity | 100% | 有 chunks 时引用真实 |

## 技术栈

| 层 | 技术 |
|----|------|
| LLM | DeepSeek API / OpenAI（兼容） |
| Embedding | BGE-small-en-v1.5（本地 384 维） |
| 向量数据库 | PostgreSQL + PGVector |
| OCR | RapidOCR / Tesseract |
| PDF 解析 | PyMuPDF |
| 后端框架 | FastAPI + SQLAlchemy |
| 工作流引擎 | 自研 Workflow Engine（HITL + Trace + Checkpoint） |
| 前端 | React + Vite + TypeScript |
| 容器化 | Docker Compose |

## 许可证

[Apache License 2.0](LICENSE)
