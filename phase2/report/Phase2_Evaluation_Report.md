# Phase 2 Evaluation Report

## 1. Scope and Goal
This phase builds a baseline RAG pipeline over a corpus of PDF sources on AI and supply chain performance. The system ingests documents, chunks text, embeds and indexes chunks, retrieves evidence, produces citation-backed answers, and logs runs. The evaluation focuses on retrieval traceability and citation use.

## 2. Corpus and Manifest
The corpus includes 16 PDFs stored under data/raw. A data manifest is provided at data/data_manifest.csv with source IDs and local raw paths. The current manifest now includes extracted titles and authors from the PDFs, and may still benefit from manual cleanup for affiliation noise and formatting artifacts.

## 3. Ingestion and Chunking
Ingestion reads PDFs, normalizes whitespace, and writes processed text to data/processed. Chunking uses fixed-length character windows with overlap to preserve local context. Each chunk receives a source_id and chunk_id and is stored in data/processed/chunks.jsonl.

## 4. Retrieval and Generation
Chunks are embedded with SentenceTransformers (all-MiniLM-L6-v2) and indexed with FAISS (IndexFlatIP). Retrieval returns top-k chunks by cosine similarity. Answers are generated in two modes:
- LLM mode when OPENAI_API_KEY is set, with strict citation requirements
- Extractive mode when no API key is present, returning cited snippets directly

## 5. Enhancement
An enhancement stage reranks retrieved chunks using a combined score of vector similarity and lexical overlap between query terms and chunk text. This step aims to promote evidence that shares more query terms without discarding the semantic search backbone.

## 6. Evaluation Set
The evaluation set includes 20 queries in data/eval/queries.jsonl:
- 10 direct queries about AI methods, metrics, and outcomes
- 5 synthesis queries that compare or integrate sources
- 5 edge-case queries that test missing or adverse evidence

## 7. Metrics
Two lightweight metrics are computed for each query:
- Citation coverage: number of cited chunk IDs in the answer divided by retrieved evidence count
- Evidence count: number of retrieved chunks (top-k)

These metrics are reported as averages in outputs/eval_summary.json. Full per-query results are stored in outputs/eval_results.jsonl and logs are stored in logs/runs.jsonl.
Note: Citation coverage can exceed 1.0 because the numerator counts all cited chunk IDs parsed from the answer, which may include more citations than the top-k retrieved count or repeated citations across lines, so the ratio is not capped.

## 8. Results
Baseline summary (outputs/eval_summary_baseline.json):
- num_queries: 20
- avg_citation_coverage: 1.13
- avg_evidence_count: 5.0

Reranked summary (outputs/eval_summary.json):
- num_queries: 20
- avg_citation_coverage: 1.13
- avg_evidence_count: 5.0

Observed effect: the lexical reranking did not change the aggregate metrics for this run. Because the answers are extractive when no LLM key is set, most retrieved chunks are already cited, which limits movement in the coverage metric. Future runs with LLM generation may show more sensitivity to reranking.

## 9. Failure Modes and Examples
Common failure modes in outputs/eval_results.jsonl include:
- Overly generic evidence snippets that do not directly answer the query
- Citations anchored to broad literature review sections rather than specific findings
- Edge-case queries that should yield explicit “no evidence” responses but instead return unrelated context

These are visible in the retrieved_chunks field and the associated chunk text for each query.

## 10. Limitations and Next Steps
- Metadata completeness: the manifest needs authoritative titles, authors, and venues.
- Evidence precision: the current chunking is purely length-based; section-aware chunking could improve citations.
- Metrics: add groundedness scoring or citation precision with manual labels on a subset.
- Enhancement impact: test reranking with an LLM generation mode to measure improvements in faithfulness and relevance.
