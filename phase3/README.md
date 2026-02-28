# Phase 3 - Personal Research Portal

## Overview
This Phase 3 deliverable turns the Phase 2 RAG pipeline into a usable portal for research workflows. The UI supports asking questions, searching evidence, viewing citations, saving research threads, generating a research artifact, and exporting outputs.

## Features
- Ask: generate citation-backed answers with evidence snippets.
- Search: retrieve top-k evidence passages with source and chunk IDs.
- Artifacts: generate an evidence table artifact and export as CSV and Markdown.
- Evaluation: run the query set and summarize citation coverage.
- History: keep session history and export it to disk.
- Trust behavior: explicitly reports when evidence is missing and suggests refining the query.

## Quick Start
1) Install dependencies
```
pip install -r requirements.txt
```

2) Run the portal
```
streamlit run src/portal_app.py
```

## Optional LLM Answers
If you want LLM-generated answers instead of extractive snippets:
- Set `OPENAI_API_KEY`
- Optionally set `OPENAI_MODEL` (default: gpt-4o-mini)

## Stable API Key Setup
You can provide the API key in either of these persistent ways:

### Option A: .env in phase3 root
Create a `.env` file under `phase3/`:
```
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

### Option B: Streamlit secrets
Create `.streamlit/secrets.toml` under `phase3/`:
```
OPENAI_API_KEY="your_key_here"
OPENAI_MODEL="gpt-4o-mini"
```

Restart the Streamlit app after updating the key.

## Example Questions
- What evidence links AI to improved supply chain performance?
- Which papers discuss demand forecasting and what metrics do they report?
- Compare reinforcement learning vs. supervised learning approaches in inventory control.
- Does the corpus contain evidence about AI’s impact on lead time variability?
- What are common limitations reported in AI-based supply chain optimization studies?
- Which sources report real-world deployment results vs. simulations?
- What datasets are used for supply chain demand forecasting in this corpus?
- Where do papers disagree on AI impact on resilience or risk mitigation?
- What evidence supports multi-objective optimization in logistics?

## Project Structure
```
phase3/
  data/
    raw/                # PDFs and source artifacts
    processed/          # extracted text, chunks, FAISS index
    eval/queries.jsonl  # evaluation queries
    data_manifest.csv   # source metadata
  src/
    portal_app.py       # Phase 3 UI
    rag/                # retrieval + answer generation
    ingest/             # ingestion and chunking
    eval/               # evaluation runner
  outputs/
    exports/            # artifact exports (CSV/MD)
    threads.jsonl       # saved research threads
    history.jsonl       # exported UI history
    eval_*_portal.json  # evaluation outputs
  logs/
    runs.jsonl          # run logs
```

## Outputs
The portal writes files under `outputs/`:
- `exports/evidence_table_*.csv`, `exports/evidence_table_*.md`, and `exports/evidence_table_*.pdf`
- `threads.jsonl` for saved threads
- `history.jsonl` for exported UI history
- `eval_results_portal.jsonl` and `eval_summary_portal.json`

## Notes
- The portal reuses the Phase 2 index and processed data under `data/processed/`.
- Evidence citations follow the format `(source_id, chunk_id)` and map to `data/processed/chunks.jsonl`.
