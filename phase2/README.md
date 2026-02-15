# Phase 2 - Ground the Domain (Research-Grade RAG)

## Overview
This Phase 2 implementation builds a baseline RAG pipeline over a PDF corpus on AI and supply chain performance. It ingests sources with metadata, chunks text, embeds and indexes chunks, retrieves evidence, generates citation-backed answers, and logs runs. An enhancement stage adds lexical reranking of retrieved chunks.

## Project Structure
data/raw/ contains PDFs
data/processed/ contains extracted text, chunks, and index
data/data_manifest.csv contains source metadata
data/eval/queries.jsonl contains 20 evaluation queries
src/ingest contains ingestion and chunking
src/rag contains indexing, retrieval, and answer generation
src/eval contains evaluation runner
logs/ contains run logs
outputs/ contains evaluation outputs

## Setup
Install dependencies:
pip install -r requirements.txt

If you want LLM answers, set OPENAI_API_KEY and optionally OPENAI_MODEL.

## Run Pipeline
1) Ingest and chunk:
python src/ingest/ingest_pipeline.py

2) Build index:
python src/rag/build_index.py

3) Run a single query:
python src/rag/run_query.py --query "What evidence links AI to improved supply chain performance?"

4) Run evaluation set:
python src/eval/run_eval.py

## Outputs
data/processed/chunks.jsonl
data/processed/index.faiss
logs/runs.jsonl
outputs/eval_results.jsonl
outputs/eval_summary.json

## Enhancement Implemented
Lexical reranking reorders retrieved chunks by combining vector similarity with keyword overlap between the query and chunk text. The reranked outputs are saved in the standard evaluation files.
