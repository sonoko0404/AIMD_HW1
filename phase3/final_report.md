# Phase 3 Final Report — Personal Research Portal

## 1. Overview
This report documents the design, implementation, and evaluation of the **Personal Research Portal (PRP)**, a specialized Retrieval-Augmented Generation (RAG) system tailored for the domain of **"AI in Supply Chain"**.

The primary goal of this system is to accelerate the research workflow by automating the synthesis of evidence from academic literature. Unlike generic chatbots (e.g., ChatGPT), the PRP is designed to be **grounded, verifiable, and hallucination-resistant**. It ingests a curated corpus of PDF papers, indexes them for semantic search, and provides a citation-backed answer generation engine.

The system serves four key user needs:
1.  **Discovery**: Finding relevant snippets across dozens of papers instantly.
2.  **Synthesis**: Answering complex research questions (e.g., "What are the limitations of RL in inventory management?") with consolidated evidence.
3.  **Verification**: Providing inline citations `(SourceID, ChunkID)` that map directly to the source text.
4.  **Artifact Generation**: Automatically producing structured evidence tables for literature reviews.

---

## 2. System Architecture
The system follows a modular RAG pipeline architecture, implemented in Python 3.10+. The architecture is divided into offline (Ingestion, Indexing) and online (Retrieval, Generation) components.

### 2.1 Data Ingestion Layer (`src/ingest/ingest_pipeline.py`)
The ingestion pipeline is responsible for converting unstructured raw files into clean, structured text chunks.

*   **Manifest-Driven Processing**: The system reads `data/data_manifest.csv` to identify valid sources. This ensures that only authorized documents are processed and allows for metadata association (Title, Year, DOI) right from the start.
*   **PDF Parsing**: We utilize `pypdf` to extract text. To address common PDF artifacts, a custom normalization function `normalize_text()` is applied:
    *   **De-hyphenation**: Regex `r"(\w)-\s+(\w)"` repairs words split across line breaks (e.g., "opti- mization" → "optimization").
    *   **Whitespace Cleaning**: Collapses multiple spaces and newlines into single spaces to maintain semantic continuity for the embedding model.
*   **Sliding Window Chunking**:
    *   **Strategy**: Fixed-size character window.
    *   **Parameters**: `chunk_size=1000`, `overlap=150`.
    *   **Boundary Detection**: The chunker explicitly checks for whitespace `text[right].isspace()` before splitting, ensuring that words are never truncated mid-token. This is critical for embedding quality, as "network" and "net-" + "work" map to very different vector spaces.

### 2.2 Indexing Layer (`src/rag/build_index.py`)
The indexing layer transforms text into vector representations for efficient similarity search.

*   **Embedding Model**: We employ `sentence-transformers/all-MiniLM-L6-v2`.
    *   **Dimensions**: 384.
    *   **Performance**: This model balances speed (inference <10ms on CPU) with strong semantic understanding. It is specifically trained for asymmetric semantic search (short query, long passage).
*   **Vector Store**: **FAISS (Facebook AI Similarity Search)**.
    *   **Index Type**: `IndexFlatIP` (Inner Product).
    *   **Metric**: Since embeddings are normalized via `normalize_embeddings=True` during encoding, the Inner Product operation is mathematically equivalent to **Cosine Similarity**.
    *   **Storage**: The index is serialized to disk (`data/processed/index.faiss`) alongside a JSONL metadata file (`chunks_meta.jsonl`) that maps vector IDs back to text and source metadata.

### 2.3 Retrieval & Reranking Engine (`src/rag/engine.py`)
The retrieval engine implements a two-stage process to maximize relevance.

*   **Stage 1: Dense Retrieval (Recall)**
    *   The user's query is encoded into a 384-d vector.
    *   FAISS performs an exact nearest neighbor search to retrieve the top-**k** (default k=5) candidates based on semantic similarity.
*   **Stage 2: Hybrid Reranking (Precision)**
    *   A custom heuristic reranker scores each retrieved chunk using a weighted formula:
        $$ Score = 0.7 \times \text{VectorScore} + 0.3 \times \text{KeywordOverlap} $$
    *   **Keyword Overlap**: Calculated as the intersection of alphanumeric tokens between the query and the chunk text.
    *   **Rationale**: This mechanism penalizes "semantically broad" but "lexically missing" results. For example, if a user asks for "LSTM", a chunk discussing "Recurrent Neural Networks" might have high vector similarity, but a chunk explicitly containing "LSTM" should be prioritized.

### 2.4 Generation Layer (`src/rag/engine.py`)
The generation layer synthesizes the answer using **OpenAI's GPT-4o-mini**.

*   **Prompt Engineering**:
    *   **Role**: "You are a research assistant."
    *   **Constraint**: "Use only the provided context."
    *   **Citation Format**: "Every major claim must include an inline citation as (source_id, chunk_id)."
    *   **Negative Constraint**: "If evidence is missing, say so, do not guess."
*   **Context Construction**: Retrieved chunks are formatted as `[{chunk_id}] {text}` to allow the LLM to reference specific segments accurately.
*   **Temperature**: Set to **0.2** to minimize creativity and maximize factual adherence.

### 2.5 Application Layer (`portal_app.py`)
The user interface is built with **Streamlit**, providing a reactive web experience.
*   **State Management**: `st.cache_resource` is used to load the `RAGEngine` only once, preventing expensive model reloading on every interaction.
*   **Configuration**: The app supports API keys via both `.env` files and `st.secrets`, enabling secure deployment.
*   **Observability**: Every query, answer, and retrieved set is logged to `logs/runs.jsonl` with a timestamp and prompt ID. This creates a valuable dataset for future fine-tuning or analysis.
*   **Artifact Generation**: The "Artifacts" tab uses a specialized sub-routine (`build_evidence_rows`) that makes secondary LLM calls (temperature 0.1) to extract atomic "one-sentence claims" for the evidence table, ensuring high-density information export.

---

## 3. Design Choices & Trade-offs

### 3.1 Embedding Model: `all-MiniLM-L6-v2`
*   **Choice**: A small, local BERT-based model (80MB).
*   **Rationale**:
    *   **Speed**: Encoding is fast enough to run on a standard laptop CPU without noticeable latency.
    *   **Cost**: Zero inference cost compared to API-based embeddings (e.g., OpenAI `text-embedding-3`).
    *   **Privacy**: Embeddings are generated locally; the full corpus content is never sent to an external API during indexing.
*   **Trade-off**: It has a smaller context window and lower semantic nuance than massive models (e.g., OpenAI, Cohere). It may struggle with very subtle domain-specific distinctions (e.g., "stochastic" vs "probabilistic" in complex contexts).

### 3.2 Vector Index: Flat vs. IVF
*   **Choice**: FAISS `IndexFlatIP` (Exact Search).
*   **Rationale**:
    *   **Accuracy**: Returns the *mathematically guaranteed* nearest neighbors. No approximation error.
    *   **Simplicity**: No training phase required (unlike IVF or HNSW).
*   **Trade-off**: Linear search complexity ($O(N)$). While perfectly fine for our corpus (<10,000 chunks), this would become a bottleneck at scale (>1M chunks), necessitating an approximate index (HNSW).

### 3.3 Chunking Strategy: Large (1000 chars) + Overlap
*   **Choice**: 1000 characters with 150 overlap.
*   **Rationale**:
    *   **Context Preservation**: Academic claims are often verbose. A 256-char chunk might capture "The model achieved 95% accuracy" but miss *which model* was being discussed in the previous sentence. 1000 chars captures the full "Subject-Verb-Object-Condition" structure.
    *   **Overlap**: Mitigates the risk of splitting a key definition or formula in half.
*   **Trade-off**: "Dilution". A 1000-char chunk containing one relevant sentence and 10 irrelevant ones introduces noise into the LLM context window.

### 3.4 Hybrid Reranking
*   **Choice**: Weighted sum of Vector Score (70%) and Keyword Jaccard Index (30%).
*   **Rationale**: Pure vector search suffers from "semantic drift" — retrieving topically related but specific-detail-missing chunks. The keyword boost acts as a "soft filter," ensuring that if the user types a specific acronym (e.g., "SVM"), chunks containing that string rise to the top.
*   **Trade-off**: It is a heuristic, not a learned model. It doesn't understand synonyms (e.g., "AI" vs "Artificial Intelligence") in the keyword component, though the vector component compensates for this.

---

## 4. Evaluation

### 4.1 Methodology
We implemented a rigorous evaluation pipeline (`src/eval/run_eval.py`) using a "golden set" of 20 queries (`data/eval/queries.jsonl`).
*   **Metrics**:
    1.  **Evidence Count**: The raw number of chunks retrieved (fixed at k=5).
    2.  **Citation Coverage**: Defined as $\frac{|Unique Chunks Cited|}{|Total Chunks Retrieved|}$.
*   **Interpretation**:
    *   **High Coverage (>0.8)**: The retrieval is extremely precise; almost every chunk retrieved was useful enough to be cited.
    *   **Low Coverage (<0.2)**: The retrieval is noisy; the LLM had to ignore most of the provided text.

### 4.2 Quantitative Results
*   **Queries Run**: 20
*   **Avg. Citation Coverage**: **0.30 (30%)**
*   **Avg. Evidence Count**: 5.0

### 4.3 Qualitative Analysis
The 30% coverage metric indicates that for every 5 chunks retrieved, approximately **1.5 are cited** and 3.5 are discarded by the LLM.

*   **Success Case (High Precision)**:
    *   *Query*: "What AI methods are reported to improve demand forecasting...?" (Q001)
    *   *Result*: The system retrieved chunks listing specific models (CNN, LSTM, GRU). The answer synthesized these into a coherent list. The keyword "forecasting" likely helped the reranker align the vector results.
*   **Partial Failure (Broad Retrieval)**:
    *   *Query*: "What organizational or human factors influence AI effectiveness...?" (Q009)
    *   *Result*: The system retrieved generic "future work" sections mentioning "human factors" but lacked deep empirical evidence. The LLM correctly identified this, stating "metrics are not detailed." This is a **success of the prompt engineering** (avoiding hallucination) but a **limitation of the corpus/retrieval** (content not present or not found).
*   **The "Zero-Shot" Behavior**:
    *   In cases where no relevant info was found (e.g., specific inventory metrics in Q002), the system returned a "I cannot answer" response. This is preferable to a hallucinated answer in a research context.

---

## 5. Limitations

### 5.1 Retrieval Precision ("The 30% Problem")
The current 30% citation coverage implies that **70% of our context window is wasted**.
*   **Root Cause**: The bi-encoder model (`all-MiniLM`) compresses all semantic meaning into a single vector. This "bottleneck" causes it to confuse high-level topic similarity with precise question-answering relevance.
*   **Consequence**: If the true answer lies in the 6th or 7th best chunk, it is pushed out of the top-5 window by less relevant chunks that happen to share high-level keywords.

### 5.2 PDF Parsing Artifacts
*   **Issue**: `pypdf` extracts text linearly (`page.extract_text()`).
*   **Manifestation**:
    *   **Tables**: A table with rows and columns is flattened into a stream of words, destroying the relationship between headers and cell values.
    *   **Sidebars/Footers**: Text from page footers (e.g., "Page 1 of 10") is inserted into the middle of sentences if not carefully handled.
*   **Impact**: Quantitative queries (e.g., "What was the F1 score?") often fail because the number "0.95" is separated from the label "F1 Score" in the flattened text.

### 5.3 Metadata Blindness
The current index (`IndexFlatIP`) treats all chunks equally.
*   **Issue**: Users cannot filter by Year, Author, or Venue.
*   **Scenario**: A user asking "What are the *latest* (2025) methods?" will receive results from 2021 if they are semantically similar. The embedding model does not encode "recency" as a semantic feature.

---

## 6. Next Steps

To evolve the PRP from a prototype to a production-grade research tool, we propose the following roadmap with detailed implementation strategies:

### 6.1 Phase 4: Advanced RAG (Immediate Priority)

1.  **Cross-Encoder Reranking**
    *   **Goal**: Improve precision by re-scoring the top retrieved candidates with a model that understands the relationship between query and document.
    *   **Implementation**:
        *   **Library**: `sentence-transformers` (CrossEncoder class).
        *   **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (fast and effective).
        *   **Workflow Modification**:
            1.  **Recall**: Retrieve **Top-50** chunks using the existing FAISS index (instead of Top-5).
            2.  **Rerank**: Pass 50 pairs of `(query, chunk_text)` to the Cross-Encoder.
            3.  **Sort**: Re-order based on the model's output logits.
            4.  **Cut**: Select the **Top-5** highest-scoring chunks for the LLM context.
        *   **Code Location**: Update `src/rag/engine.py`, specifically replacing the heuristic `rerank()` method.

2.  **Hybrid Search with BM25**
    *   **Goal**: Fix the "keyword blindness" of vector search by incorporating exact term matching.
    *   **Implementation**:
        *   **Library**: `rank_bm25` (Okapi BM25 implementation).
        *   **Workflow Modification**:
            1.  **Indexing**: During `build_index.py`, tokenize all chunks and build a `BM25Okapi` object. Save it via `pickle`.
            2.  **Retrieval**:
                *   Get Vector Scores ($S_{vec}$) from FAISS.
                *   Get BM25 Scores ($S_{bm25}$) for the same query.
                *   **Normalization**: Min-Max normalize both score sets to [0, 1] range to make them comparable.
                *   **Fusion**: Calculate Final Score using Reciprocal Rank Fusion (RRF) or Weighted Sum:
                    $$ S_{final} = 0.7 \cdot S_{vec} + 0.3 \cdot S_{bm25} $$
        *   **Code Location**: `src/rag/build_index.py` (index creation) and `src/rag/engine.py` (search logic).

### 6.2 Phase 5: Data Quality & Structure

3.  **Layout-Aware Parsing**
    *   **Goal**: Preserve the semantic structure of academic papers, especially tables and headers.
    *   **Implementation**:
        *   **Tool**: **Microsoft MarkItDown** or **PyMuPDF4LLM**.
        *   **Workflow Modification**:
            1.  Replace `pypdf` in `ingest_pipeline.py`.
            2.  Extract content as **Markdown** text. This preserves:
                *   Headers (`# Section 1`) -> Hierarchy.
                *   Tables (`| Col A | Col B |`) -> Structure.
                *   Lists (`- Item`) -> Grouping.
            3.  **Chunking Update**: Modify the sliding window to respect Markdown boundaries (e.g., never split inside a Markdown table).
        *   **Code Location**: `src/ingest/ingest_pipeline.py`.

4.  **Metadata Filtering**
    *   **Goal**: Enable queries like "Papers from 2024" or "Authors from MIT".
    *   **Implementation**:
        *   **Tool**: Migrate from FAISS to **ChromaDB** (local persistence mode).
        *   **Workflow Modification**:
            1.  **Indexing**: Store metadata dict `{"year": 2024, "source": "DOI..."}` alongside the vector embedding.
            2.  **Querying**: Accept a filter argument in the retrieval engine: `collection.query(query_embeddings, n_results=5, where={"year": {"$gte": 2024}})`.
            3.  **UI**: Add sidebar filters in Streamlit for Year Range and Source.
        *   **Code Location**: Replace `faiss` logic in `src/rag/build_index.py` and `src/rag/engine.py`.

### 6.3 Phase 6: Automated Evaluation & Feedback

5.  **LLM-as-a-Judge**
    *   **Goal**: Scale evaluation beyond the 20-query golden set without human effort.
    *   **Implementation**:
        *   **Method**: **G-Eval** framework using GPT-4o.
        *   **Workflow**:
            1.  Create a new script `src/eval/llm_judge.py`.
            2.  Define a rubric prompt:
                > "You are a judge. Rate the answer on a scale of 1-5 for:
                > 1. **Faithfulness**: Is it supported by the context?
                > 2. **Relevance**: Does it answer the user's question?"
            3.  Run this over `eval_results_portal.jsonl` and compute average scores.
        *   **Code Location**: New file `src/eval/llm_judge.py`.

6.  **User Feedback Loop**
    *   **Goal**: Collect real-world failure cases for future fine-tuning.
    *   **Implementation**:
        *   **UI Component**: Use `st.feedback("thumbs")` (Streamlit 1.37+) after the answer display.
        *   **Logging**:
            1.  On feedback submission, append a JSON entry to `logs/feedback.jsonl`:
                `{ "timestamp": ..., "query_id": ..., "rating": 1 (up) or -1 (down), "comment": ... }`
            2.  Review "Thumbs Down" queries weekly to improve the prompt or corpus.
        *   **Code Location**: `src/portal_app.py`.

---

## 7. Research Artifacts

The system successfully generates the following artifacts, which are included in the repository:

*   **Evidence Table (CSV)**: `outputs/exports/evidence_table_20260301_010214.csv`
    *   *Format*: Structured data ready for Excel/Pandas analysis.
*   **Evidence Table (Markdown)**: `outputs/exports/evidence_table_20260301_010214.md`
    *   *Format*: Clean, readable tables for inclusion in reports.
*   **Evidence Table (PDF)**: `outputs/exports/evidence_table_20260301_010214.pdf`
    *   *Format*: Professional report layout generated via `reportlab`.

These artifacts demonstrate the "Synthesis" capability of the system, transforming raw search results into organized knowledge representations.
