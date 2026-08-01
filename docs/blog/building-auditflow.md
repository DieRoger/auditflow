---
title: "Building AuditFlow: An AI-Native Audit Engine"
description: "Engineering lessons from building a multi-agent audit system — why citations must be grounded, why evaluation must drive development, and why system integration matters more than adding features."
date: "2026-07-28"
tags:
  - AI
  - LLM
  - Agent
  - RAG
  - Evaluation
  - Architecture
  - Engineering
categories:
  - Build Log
  - Architecture
  - Engineering Decisions
slug: building-auditflow-ai-audit-engine
draft: false
author: Luo Runjie
readingTime: 25
difficulty: Advanced
---

## Background

When I started AuditFlow, I had a straightforward question: could we build an AI system that does more than *answer questions* about financial documents — could it actually *perform an audit*?

Most LLM applications at the time followed a familiar pattern: ingest documents → chunk → embed → retrieve → generate answer. This works well for Q&A bots, but audit is different. An audit isn't a single question. It's a multi-step reasoning process that involves understanding a business, identifying risks, collecting evidence, forming conclusions, and documenting everything in a traceable way.

In audit, every conclusion must be supported by evidence. Every evidence must point to a specific document, page, and paragraph. The reasoning chain must be inspectable by a human reviewer. And the final output — an audit report — must follow professional standards like ISA 700.

Generic RAG couldn't satisfy these requirements. So I built AuditFlow: an AI-native audit intelligence platform with a multi-agent workflow, evidence-grounded citations, and an evaluation-driven development process.

This article documents the engineering journey — the architecture decisions, the failures, the fixes, and the lessons learned.

---

## Initial Design: The Five-Agent Pipeline

The first architectural decision was the agent structure. Instead of a single monolithic LLM prompt, I decomposed the audit workflow into five specialized agents:

```
Planner    —  Task decomposition
Knowledge  —  Standards retrieval
Risk       —  Risk identification
Evidence   —  Claim-evidence matching
Reviewer   —  Quality control and hallucination detection
```

Each agent followed the same contract: a typed input schema, a typed output schema, and a list of declared tools. Agents never called each other directly — they communicated through a Workflow Engine that managed state, context, and execution order.

The Workflow Engine itself was a state machine with eight states (`CREATED → QUEUED → RUNNING → WAITING_APPROVAL → RETRYING → FAILED → COMPLETED → CANCELLED`), checkpoint/restore for fault tolerance, and a human-in-the-loop gate for high-risk decisions.

Early on, I considered using LangGraph for the workflow layer. I chose a custom engine instead, because:

| Factor | LangGraph | Custom Engine |
|--------|-----------|---------------|
| Control over state transitions | Limited to graph API | Full control |
| HITL integration | Requires LangGraph Cloud | Native in engine |
| Checkpoint granularity | Per graph node | Per agent execution |
| Dependency weight | ~200MB with all extras | Zero |

The trade-off was development speed vs. long-term flexibility. For a research project where the workflow requirements were still evolving, custom control was more important than reducing initial code.

---

## Problem 1: The Fake Citation Crisis

The first version of AuditFlow worked. The five agents called DeepSeek, produced risk assessments, and generated reports. The demo looked convincing.

But when I inspected the output more carefully, I found a critical flaw:

```python
# What the code did:
Citation(
    document_id="llm_analysis",  # ← invented by LLM
    page=0,
    chunk_id="unknown"
)
```

The Risk Agent was generating citations that *looked* real — they had document IDs, page numbers, and confidence scores — but none of them corresponded to actual documents. The LLM was fabricating citations because its prompt asked it to "provide supporting citations," and being helpful, it complied with plausible-sounding but entirely fake references.

This is a well-known problem in RAG systems, but it's especially dangerous in audit. A fake citation in a chatbot is embarrassing. A fake citation in an audit workpaper could have legal consequences.

### The Fix: Evidence-Chunked Prompting

The solution was to restructure the Risk Agent's prompt to separate evidence retrieval from reasoning:

1. Before the agent runs, retrieve relevant document chunks from PGVector
2. Inject the chunks into the agent's context as `UNTRUSTED_DATA`
3. The LLM can only output `evidence_chunk_indices` — an index into the provided chunks
4. The system maps indices back to actual document IDs, page numbers, and excerpts

```python
# Old prompt (LLM generates citations):
"Identify risks and provide supporting citations."

# New prompt (LLM selects from evidence):
"Identify risks. For each risk, list the indices of document excerpts 
(0, 1, 2...) that support your conclusion. Do not invent citations."
```

The system then fills in the citation metadata:

```python
for idx in chunk_indices:
    chunk = chunks[idx]
    citations.append(Citation(
        document_id=chunk.document_id,
        page=chunk.page_number,        # real page from PDF
        chunk_id=chunk.chunk_id,         # real UUID from PGVector
        confidence=chunk.score,          # real cosine similarity
    ))
```

This change eliminated fabricated citations. Every citation now points to a real page in a real document, with a measurable similarity score.

### Measuring the Impact

| Metric | Before (fake citations) | After (grounded) |
|--------|------------------------|------------------|
| Citation Validity | 0% (all `llm_analysis`) | 100% |
| Citation Support | N/A | 88% |
| Hallucination Risk | Unknown | 21% (measured) |

---

## Problem 2: The Chunk-Thinking Gap

The initial document pipeline parsed PDFs, split them into chunks, and embedded them for retrieval. But the chunking was naive — one chunk per page, regardless of content structure.

This caused two problems:

1. **Semantic breaks**: A paragraph about revenue recognition could be split mid-sentence across two chunks
2. **Retrieval blind spots**: A question about "contract modifications" wouldn't find the chunk containing "cumulative catch-up method" if they were on different pages

### The Fix: Semantic Chunking with Paragraph Detection

I replaced the page-based splitter with a paragraph-aware chunker:

```python
def chunk_text(text, page_number, max_tokens=500, overlap_tokens=50):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    # Merge short paragraphs, respect natural boundaries
    for para in paragraphs:
        if current_tokens + estimate_tokens(para) > max_tokens:
            # flush current chunk, start new one
            # overlap: carry last paragraph to next chunk
```

Key parameters: `max_tokens=500` (fits comfortably in context windows), `overlap_tokens=50` (preserves boundary context).

---

## Problem 3: The Evaluation Gap

The most humbling moment came when I ran the first formal evaluation. I had 8 benchmark cases — each with a financial scenario, expected risks, and expected severity. The Risk Agent scored:

| Metric | Score |
|--------|-------|
| Risk Classification | 0% |
| Severity Accuracy | 0% |
| Citation Completeness | 0% |

Zero across the board. The evaluation framework was working correctly — it was measuring what the system actually produced, not what I hoped it would produce. The problem was that the metrics expected a specific output format that the agent wasn't producing.

This forced a critical shift in how I thought about development. Before the evaluation, I was iterating by feel — tweaking prompts, adding features, relying on manual demos. After the evaluation, I had objective numbers. I could say "this change improved severity accuracy from 40% to 75%" instead of "this feels better."

### Building the Evaluation Stack

I built a three-layer evaluation framework:

**Layer 1 — Retrieval Metrics** (Recall@K, MRR, NDCG): How well does the vector search find relevant chunks?

**Layer 2 — Agent Metrics** (Risk Classification Accuracy, Severity Accuracy, Citation Completeness): How well do agents produce correct outputs?

**Layer 3 — Grounding Metrics** (Citation Precision, Citation Recall, Unsupported Claim Rate): How well are claims supported by evidence?

Each layer feeds into the next. Weak retrieval (Layer 1) limits agent accuracy (Layer 2), which limits grounding quality (Layer 3).

### Consistency Testing

An underappreciated metric: consistency. Run the same case twice — do you get the same answer?

```
Consistency Test Results (8 cases × 2 runs):
  Risk Consistency:      75%
  Severity Consistency: 100%
```

100% severity consistency means the model reliably gives the same severity level for the same scenario. 75% risk consistency means the risk title can vary — a problem when specific risk names are expected.

### Human Evaluation

For the final validation, I annotated 10 cases manually with gold-standard answers based on Chinese auditing standards (CAS) and International Standards on Auditing (ISA). The evaluation measured how well the system's outputs matched human expert expectations:

| Metric | Score |
|--------|-------|
| Severity Agreement | 80% |
| Evidence Recall | 78% |
| Risk Classification | 35% |

The 35% risk classification score looks low, but it reveals an important tension: the LLM generates specific, contextualized risk descriptions (e.g., "Inadequate Allowance for Doubtful Accounts"), while the gold standard uses broader categories (e.g., "Accounts Receivable Risk"). Neither is wrong — they're operating at different granularity levels. A matching metric based on semantic similarity rather than keyword overlap would likely show higher agreement.

---

## Document Pipeline: OCR Reality

One of the most underestimated parts of the system was document processing. Financial documents come in varied formats:

| Type | Proportion | Approach |
|------|-----------|----------|
| Digital PDF (text layer) | ~80% | PyMuPDF direct extraction |
| Scanned PDF (no text) | ~10% | OCR with RapidOCR |
| Hybrid (text + images) | ~10% | Page-level detection, selective OCR |

The OCR choice was interesting. I started with Tesseract, which worked but had poor Chinese accuracy (~75%). Python environment issues made PaddlePaddle impractical. The final solution was **RapidOCR** — an ONNX-based OCR engine that requires no deep learning framework:

```python
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
# ~95% Chinese accuracy, 384KB model, zero PyTorch dependencies
```

---

## Architecture Decisions

### PGVector over FAISS

| Criteria | PGVector | FAISS |
|----------|----------|-------|
| Storage | In PostgreSQL | Separate index file |
| Filtering | SQL WHERE clauses | Custom implementation |
| ACID compliance | Native | Not supported |
| Deployment | Same DB as app data | Separate service |
| HNSW index | Supported | Supported |

For a system where every query needs tenant isolation (`WHERE tenant_id = ?`), PGVector's native SQL filtering was decisive. FAISS would require a separate metadata filtering layer.

### Local Embedding over API

I chose `BAAI/bge-small-en-v1.5` (384-dim, local inference) over OpenAI's `text-embedding-3-large` (3072-dim, API):

- **Cost**: $0 vs ~$0.13/1M tokens
- **Latency**: ~5ms vs ~500ms (network)
- **Privacy**: Data stays local vs leaves the network
- **Dimension**: 384 vs 3072 (smaller, faster similarity search)

The trade-off is accuracy. BGE-small has lower retrieval precision than OpenAI's large embedding model. For this project, the trade-off was acceptable — the cost savings and privacy guarantees were more important than marginal recall improvements.

### DeepSeek over OpenAI

The primary LLM is DeepSeek (via compatible OpenAI SDK):

```python
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)
```

Key consideration: DeepSeek provides a comparable model at significantly lower cost (~$0.28/M tokens vs ~$2.50/M tokens for GPT-4). The system supports fallback to OpenAI if DeepSeek is unavailable.

---

## What Didn't Work

Not every decision was correct. Here are the notable failures:

### 1. Over-Engineering the Architecture

The initial repository structure had 8 layers (Presentation → API → Application → Domain → AI → Knowledge → Infrastructure → Platform). This was too many for a solo project. The `application/` layer stayed empty for months because I was spending more time on directory structure than on actual features.

**Lesson**: Start with 3-4 layers and add more as the system grows. Premature abstraction creates busywork.

### 2. Hardcoded API Keys in Demo Scripts

The first demo scripts had the DeepSeek API key hardcoded. When I pushed to GitHub, I had to scrub it from three files. The `.env` file was created but not loaded properly, causing confusing "authentication fails" errors.

**Fix**: All scripts now use `load_dotenv(override=True)` to force `.env` values over system environment variables. API keys in source code are a CI-breaking offense.

### 3. Single Workflow Model

The initial architecture assumed one workflow handles everything — indexing and querying. In practice, these are two different workflows with different latency and data requirements:

- **Index Workflow**: Upload → Parse → OCR → Chunk → Embed → Store (async, batch)
- **Query Workflow**: Question → Retrieve → Agent → Respond (synchronous, interactive)

Mixing them created complexity without benefit.

### 4. Vite TypeScript Configuration

The frontend used TypeScript with `@vitejs/plugin-react`, but the Vite esbuild transformation didn't work on the development machine (a known issue with certain Windows configurations). After hours of debugging, I abandoned TypeScript and rewrote the frontend in plain JavaScript with `React.createElement`.

**Lesson**: When a build tool doesn't work on the target machine after 30 minutes of debugging, switch to a simpler configuration. The frontend works identically — just without type checking.

---

## Key Metrics

After five development sprints, the system produces:

```
Pipeline: PDF → Parse → Chunk → Embed → 5 Agents → Workpaper → Report
Full runtime: ~50 seconds (with DeepSeek)
Total chunks indexed: ~3,000 (67 documents)
Tests: 103 passing, 1 skipped
Git commits: 13 (logical)
Lines of code: ~15,000
```

---

## Lessons Learned

1. **Evaluations find problems that demos hide.** Running the first evaluation revealed a 0% accuracy rate that manual demos had concealed. Build evaluation before building features.

2. **Citations must be grounded in retrieval, not generation.** LLMs will fabricate plausible-looking citations when asked. The only reliable approach is to decouple "which evidence supports this" (system responsibility) from "what does this evidence mean" (LLM responsibility).

3. **System integration is harder than module development.** Each component worked in isolation. Getting them to work together — Parser → Chunker → Embedder → Retriever → Agent → Evaluator — took more effort than building any single component.

4. **Consistency is an underrated metric.** A system that gives different answers for the same input is unreliable, even if each individual answer is correct. Consistency tests are cheap to run and catch real problems.

5. **Start simple, add layers as needed.** The three-layer evaluation framework (Retrieval → Agent → Grounding) emerged from actual debugging needs, not upfront design. Over-engineering the architecture delayed development without improving quality.

---

## Future Work

The current system is a functional MVP, but several areas need improvement:

- **Execution sandbox**: Agents run in the same process, risking cascading failures
- **Token budget management**: No hard limits on LLM token consumption
- **Prompt version control**: Prompts are externalized to files but not yet managed through the PromptRegistry
- **Benchmark expansion**: From 8 cases to 100+ cases with industry-standard annotations
- **Neo4j ontology**: Graph-based audit reasoning (currently SQL-based)

The project is available at [github.com/DieRoger/auditflow](https://github.com/DieRoger/auditflow).

---

## Key Takeaways

1. Grounded citations require a system-level separation of evidence selection (system) and reasoning (LLM)
2. Evaluation metrics should be built before features — they reveal problems that demos conceal
3. Multi-agent systems need more integration engineering than agent engineering
4. Consistency testing is high-value, low-cost — run it before every release
5. Start with 3 architecture layers, not 8 — premature abstraction creates overhead
