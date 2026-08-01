I spent the last few months building AuditFlow — an AI-native audit engine that goes from PDF upload to ISA-compliant audit report. Here's what went wrong and what I learned:

1/ The biggest discovery: LLMs fabricate citations. The Risk Agent was outputting document IDs like "llm_analysis" with page numbers that didn't exist. The fix? Decouple evidence selection from reasoning. LLM picks chunk indices, system fills in document IDs and page numbers from the retriever. Citation validity went from 0% → 100%.

2/ Evaluation broke my confidence before it built it. First formal run: 0% across all metrics. The system was working fine in demos — but demos don't measure. Build evaluation before features. It's the only way to know if changes actually improve things.

3/ Multi-agent sounds cool but integration is the hard part. Parser → Chunker → Embedder → Retriever → 5 Agents → Evaluator. Each piece works alone. Getting them to work together took longer than building any single component.

4/ OCR reality check: Tesseract ~75% on Chinese docs. PaddleOCR needed PyTorch that conflicted with existing deps. Ended up with RapidOCR (ONNX-based) — 95% accuracy, zero framework dependencies, tiny model.

Full story: [link to blog]
