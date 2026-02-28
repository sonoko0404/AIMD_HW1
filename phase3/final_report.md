# Phase 3 Final Report — Personal Research Portal

## 1. Overview
This Phase 3 deliverable implements a Personal Research Portal (PRP) that supports the workflow from question → evidence → synthesis → export. The portal ingests a domain corpus, retrieves evidence with citations, generates answers, produces research artifacts, and logs evaluation results. The UI is a Streamlit app with dedicated tabs for Ask, Search, Artifacts, Evaluation, and History.

## 2. System Architecture
The portal reuses the Phase 2 pipeline and adds the product layer:

1. **Ingest**  
   - Source files are listed in `data/data_manifest.csv` with metadata.  
   - Raw PDFs live in `data/raw/`.  
   - Parsed and normalized text is stored in `data/processed/*.txt`.  
   - Chunking: 1000-character chunks with 150-character overlap, aligned to word boundaries.

2. **Indexing**  
   - Embeddings are generated using `sentence-transformers/all-MiniLM-L6-v2`.  
   - Vector index is built with FAISS (`IndexFlatIP`).  
   - Chunk metadata is stored in `data/processed/chunks_meta.jsonl`.

3. **Retrieval + Rerank**  
   - Top-k retrieval from FAISS.  
   - Heuristic reranking based on query-term overlap and embedding similarity.

4. **Answering**  
   - Optional LLM (OpenAI) for citation-grounded answers.  
   - If LLM is unavailable, the system falls back to extractive evidence snippets.  
   - Citations use `(source_id, chunk_id)` and map to `data/processed/chunks.jsonl`.

5. **Artifacts & Exports**  
   - Evidence table artifact is generated from retrieved chunks.  
   - Exports include CSV/Markdown/PDF.

6. **Logging & Evaluation**  
   - Query logs: `logs/runs.jsonl`.  
   - Evaluation results: `outputs/eval_results_portal.jsonl`.  
   - Evaluation summary: `outputs/eval_summary_portal.json`.

## 3. Product Features (Phase 3 UI)
The Streamlit portal provides:

- **Ask**: Submit a research question and receive a citation-grounded answer.  
- **Search**: Keyword search returning top-k evidence with citations.  
- **Artifacts**: Evidence table generation and export to CSV/Markdown/PDF.  
- **Evaluation**: Run a predefined evaluation set and show summary metrics.  
- **History**: Local session history with export.

## 4. Research Artifact Design
**Artifact type**: Evidence table  
**Schema**:
- Claim  
- Evidence snippet  
- Citation `(source_id, chunk_id)`  
- Confidence (retrieval + rerank score)  
- Notes

The claim extraction uses a heuristic method by default, and when LLM is enabled it generates a grounded one-sentence claim strictly based on the retrieved passage. This improves the meaningfulness of claims without introducing unsupported content.

## 5. Evaluation Results
The evaluation set contains 20 queries from `data/eval/queries.jsonl`.  
Summary (latest run):

- `num_queries`: 20  
- `avg_citation_coverage`: 0.30  
- `avg_evidence_count`: 5.0  

See `outputs/eval_summary_portal.json` for the saved summary.

## 6. Artifacts Included in the Repo (Referenced Outputs)
Generated artifact outputs are included in the repo under `outputs/exports/` and referenced here:

- `outputs/exports/evidence_table_20260301_010214.csv`  
- `outputs/exports/evidence_table_20260301_010214.md`  
- `outputs/exports/evidence_table_20260301_010214.pdf`  
- `outputs/exports/evidence_table_20260301_004450.csv`  
- `outputs/exports/evidence_table_20260301_004450.md`  
- `outputs/exports/evidence_table_20260301_004450.pdf`  

These files demonstrate the artifact generation and export requirement for Phase 3.

## 7. Design Choices
- **FAISS IndexFlatIP** for reliable, fast vector search with cosine-similarity behavior on normalized embeddings.  
- **Heuristic reranker** for lightweight improvements without extra model costs.  
- **LLM optionality** to ensure the system still functions without API access.  
- **Word-boundary chunking** to avoid partial-token artifacts and improve readability.

## 8. Limitations
- The evidence-table claim extraction remains heuristic when LLM is disabled.  
- Evaluation metrics are limited to citation coverage; faithfulness/groundedness could be extended with additional automated checks.  
- Reranking is rule-based and can be replaced with learned cross-encoders for better precision.

## 9. Next Steps
- Add stronger reranking (cross-encoder or LLM reranker).  
- Expand evaluation metrics (answer relevance, groundedness scoring, citation precision).  
- Add metadata filters (year, venue, type) and faceted search.  
- Provide an annotated bibliography artifact in addition to the evidence table.
