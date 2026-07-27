<div align="center">

# AuditFlow

### AI-Native Audit Intelligence Platform

> **From Financial Statements to Audit Workpapers and Reports — End-to-End AI Audit Pipeline**

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![React](https://img.shields.io/badge/React-Frontend-blue)
![PGVector](https://img.shields.io/badge/PGVector-RAG-red)
![License](https://img.shields.io/badge/License-Apache_2.0-orange)

</div>

---

## Demo

```
PDF Upload
    ↓
Document Parsing (PyMuPDF / RapidOCR)
    ↓
Semantic Chunking
    ↓
Local Embedding (BGE 384-dim)
    ↓
PGVector Retrieval
    ↓
┌─────────────────────────────────────┐
│        Workflow Engine              │
│  Planner → Knowledge → Risk →       │
│  Evidence → Reviewer                │
└─────────────────────────────────────┘
    ↓
Audit Workpaper (Markdown)
    ↓
Audit Report (ISA 700 Compliant)
```

**Example output:** [`examples/workpaper.md`](examples/workpaper.md) · [`examples/report.md`](examples/report.md)

---

## Why AuditFlow?

Traditional LLM chatbots **answer questions**. AuditFlow **performs an audit**.

Instead of free-form responses, it produces structured, traceable outputs:

| Output | Description |
|--------|-------------|
| **Risk Assessment** | Identified risks with severity and probability |
| **Evidence Package** | Supporting document excerpts with page references |
| **Citation Chain** | Every conclusion traced to source PDF page + chunk |
| **Audit Workpaper** | Structured working papers per ISA standards |
| **Audit Report** | ISA 700 compliant independent auditor's report |

Every conclusion is grounded in retrieved evidence — no hallucinated citations.

---

## Key Features

### 📄 Document Intelligence
- **Digital PDF Parsing** — PyMuPDF with layout analysis, table extraction
- **OCR for Scanned Docs** — RapidOCR (Chinese ~95% accuracy, ONNX-based)
- **Semantic Chunking** — Paragraph-aware with overlap windows
- **Metadata Extraction** — Page numbers, font analysis, structure preservation

### 🤖 AI Workflow (5 Agents)

```
Planner    —  Decompose audit tasks
    ↓
Knowledge  —  Retrieve relevant standards from knowledge base
    ↓
Risk       —  Identify risks based on evidence (not LLM hallucination)
    ↓
Evidence   —  Match claims to supporting document chunks
    ↓
Reviewer   —  Quality review, hallucination detection, citation check
```

### 🔍 Retrieval-Augmented Generation
- **Hybrid Search** — Keyword (BM25) + Vector (cosine) + RRF Reranker
- **Local Embedding** — BAAI/bge-small-en-v1.5 (384-dim, zero API cost)
- **PGVector Store** — PostgreSQL with HNSW index for fast ANN search
- **Knowledge Base** — 67 audit PDFs indexed (CAS, CSAS, IAASB Handbooks, ISA 315)

### 📋 Evidence Grounding
Every audit finding includes a complete evidence chain:
```
Risk → Evidence → Citation → Page → Paragraph
```
Citations are **real** — they come from the retriever, not the LLM.

### ⚙️ Workflow Engine
- DAG-based execution with topological ordering
- Checkpoint/restore for fault tolerance
- Automatic retry (configurable policy)
- Human-in-the-loop approval gates
- Full execution trace + event bus

---

## Project Status

| Module | Status |
|--------|--------|
| Architecture & Design | ![100%](https://img.shields.io/badge/100%-brightgreen) |
| Agent Runtime | ![90%](https://img.shields.io/badge/90%-brightgreen) |
| Workflow Engine | ![90%](https://img.shields.io/badge/90%-brightgreen) |
| Document Pipeline | ![80%](https://img.shields.io/badge/80%-green) |
| Knowledge Base (67 PDFs) | ![100%](https://img.shields.io/badge/100%-brightgreen) |
| Retrieval | ![60%](https://img.shields.io/badge/60%-yellow) |
| Evidence Grounding | ![70%](https://img.shields.io/badge/70%-green) |
| Evaluation | ![40%](https://img.shields.io/badge/40%-orange) |
| Frontend | ![70%](https://img.shields.io/badge/70%-green) |
| Production | ![50%](https://img.shields.io/badge/50%-yellow) |

**Current MVP:** End-to-end pipeline from PDF upload to ISA-compliant audit report.

---

## Evaluation

| Metric | Score | Description |
|--------|-------|-------------|
| Risk Classification | 35% | Substring match against gold labels |
| Severity Agreement | **80%** | HIGH/MEDIUM/LOW classification |
| Evidence Recall | 78% | Key evidence keyword coverage |
| Citation Validity | **100%** | All citations from real retrieved chunks |
| Severity Consistency | **100%** | Same case, same severity (2 runs) |
| Risk Consistency | 75% | Same case, similar risk title (2 runs) |

```bash
# Quick baseline (8 cases, ~40s)
python scripts/eval_v2.py

# Consistency test (16 runs, ~80s)
python scripts/eval_v2.py --consistency

# Human evaluation (10 annotated cases, ~100s)
python scripts/human_eval.py
```

---

## Architecture

```
                   ┌──────────────────────┐
                   │     PDF Upload       │
                   └──────────┬───────────┘
                              │
                              ▼
                 ┌──────────────────────────┐
                 │  Document Intelligence   │
                 │  Parse → OCR → Chunk     │
                 └─────────────┬────────────┘
                               │
                               ▼
                 ┌──────────────────────────┐
                 │      PGVector Index      │
                 │  (BGE Embedding 384-dim) │
                 └─────────────┬────────────┘
                               │
                 ┌──────────────────────────┐
                 │    Workflow Engine       │
                 │  (DAG + HITL + Trace)    │
                 └─────────────┬────────────┘
                               │
      ┌────────────┬───────────┼───────────┬────────────┐
      │            │           │           │            │
      ▼            ▼           ▼           ▼            ▼
 Planner      Knowledge      Risk      Evidence    Reviewer
      │            │           │           │            │
      └────────────┴───────────┴───────────┴────────────┘
                               │
                               ▼
                 ┌──────────────────────────┐
                 │   Audit Report (ISA 700) │
                 └──────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker Desktop (for PostgreSQL + PGVector)
- DeepSeek API Key ([free signup](https://platform.deepseek.com/))

### Setup

```bash
git clone https://github.com/DieRoger/auditflow.git
cd auditflow

# Configure API key
cp .env.example .env
# Edit .env with your DEEPSEEK_API_KEY

# Install dependencies
cd backend
pip install -e .

# Start infrastructure (PostgreSQL + MinIO + Redis)
docker compose up postgres minio redis -d

# Run database migrations
python -m scripts.init_db
```

### Run Demo

```bash
cd backend
export PYTHONPATH=src

# E2E pipeline: PDF → Audit Report (~50s)
python scripts/full_demo.py

# Real PDF retrieval + Agent pipeline
python scripts/sprint1_demo.py

# Workflow engine verification
python scripts/bringup.py
```

### Start Full Stack

```bash
# Backend API (FastAPI)
cd backend
DATABASE_URL=postgresql+asyncpg://auditflow:auditflow@localhost:5432/auditflow \
  uvicorn src.main:app --port 8000

# Frontend (React + Vite)
cd frontend
npm install && npm run dev
```

---

## Repository Structure

```
auditflow/
├── backend/
│   ├── src/
│   │   ├── agents/          # 5 LLM Agents (Planner/Knowledge/Risk/Evidence/Reviewer)
│   │   ├── workflows/       # Workflow Engine (DAG + HITL + Trace + Checkpoint)
│   │   ├── infrastructure/  # LLM/OCR/Vector DB/Parser/Retrieval/Evidence
│   │   ├── evaluation/      # Metrics, Runner, Experiment Tracker
│   │   ├── services/        # Workpaper/Report Generator, Planning Engine
│   │   ├── api/             # FastAPI Routers (agents, documents)
│   │   └── domain/          # Domain models, contracts, events, artifacts
│   ├── scripts/             # Demo & evaluation scripts
│   └── tests/               # 100+ unit & integration tests
├── frontend/                # React + Vite + TypeScript
├── datasets/                # 67 knowledge base PDFs (CAS/CSAS/IAASB/ISA)
├── docs/                    # Architecture ADRs, API specs, issue tracking
├── examples/                # Sample outputs (workpaper, report)
└── docker-compose.yml       # PostgreSQL(PGVector) + MinIO + Redis
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | DeepSeek API (primary) / OpenAI (fallback) |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy (async) |
| **Vector DB** | PostgreSQL 17 + PGVector (HNSW index) |
| **Embedding** | BAAI/bge-small-en-v1.5 (384-dim, local, zero-cost) |
| **OCR** | RapidOCR (ONNX) / Tesseract |
| **PDF** | PyMuPDF (fitz) |
| **Frontend** | React 18, Vite, TypeScript |
| **Workflow** | Custom DAG Engine (Checkpoint + HITL + Trace) |
| **Infrastructure** | Docker Compose (PostgreSQL, MinIO, Redis) |
| **Object Storage** | MinIO |
| **Cache** | Redis |

---

## Roadmap

- [x] Core architecture & domain models
- [x] 5 Agent pipeline with DeepSeek integration
- [x] Document pipeline (PDF → Chunk → Embed → Index)
- [x] PGVector retrieval with hybrid search
- [x] Evidence grounding with real citations
- [x] End-to-end demo (PDF → Audit Report)
- [x] Evaluation framework (Risk/Severity/Citation/Consistency)
- [ ] Human evaluation with 100+ cases
- [ ] Ontology reasoning (Neo4j graph)
- [ ] Multi-modal audit (Excel, images)
- [ ] MCP (Model Context Protocol) integration
- [ ] AI Copilot mode for interactive audit

---

## License

[Apache License 2.0](LICENSE)
