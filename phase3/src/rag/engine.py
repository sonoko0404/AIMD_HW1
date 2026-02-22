from pathlib import Path
import json
import os
import re
import time
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv


class RAGEngine:
    def __init__(self, top_k=5, model_name="all-MiniLM-L6-v2"):
        self.root = Path(__file__).resolve().parents[2]
        self.top_k = top_k
        self.model = SentenceTransformer(model_name)
        index_path = self.root / "data" / "processed" / "index.faiss"
        meta_path = self.root / "data" / "processed" / "chunks_meta.jsonl"
        if not index_path.exists():
            raise FileNotFoundError(str(index_path))
        if not meta_path.exists():
            raise FileNotFoundError(str(meta_path))
        self.index = faiss.read_index(str(index_path))
        self.meta = []
        with meta_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.meta.append(json.loads(line))
        load_dotenv()

    def retrieve(self, query):
        query_emb = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        ).astype(np.float32)
        scores, indices = self.index.search(query_emb, self.top_k)
        results = []
        for rank, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.meta):
                continue
            item = dict(self.meta[idx])
            item["score"] = float(scores[0][rank])
            results.append(item)
        if results:
            results = self.rerank(query, results)
        return results

    def rerank(self, query, results):
        query_terms = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
        if not query_terms:
            return results
        scored = []
        for item in results:
            text_terms = set(re.findall(r"[a-zA-Z0-9]+", item["text"].lower()))
            overlap = len(query_terms & text_terms) / max(1, len(query_terms))
            combined = 0.7 * item["score"] + 0.3 * overlap
            updated = dict(item)
            updated["rerank_score"] = combined
            scored.append(updated)
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored

    def generate_answer(self, query, results, use_llm=True):
        if use_llm and os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                client = OpenAI()
                context_lines = []
                for r in results:
                    context_lines.append(f"[{r['chunk_id']}] {r['text']}")
                context = "\n".join(context_lines)
                prompt = (
                    "You are a research assistant. Use only the provided context. "
                    "Every major claim must include an inline citation as (source_id, chunk_id). "
                    "If evidence is missing, say so and do not guess.\n\n"
                    f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"
                )
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
                return resp.choices[0].message.content.strip()
            except Exception:
                return self.extractive_answer(query, results)
        return self.extractive_answer(query, results)

    def extractive_answer(self, query, results):
        if not results:
            return (
                "No evidence found in the corpus. Suggested next step: refine the query "
                "with specific methods, datasets, metrics, or years."
            )
        lines = []
        for r in results:
            snippet = r["text"][:260].strip()
            lines.append(
                f"{snippet} ({r['source_id']}, {r['chunk_id']})"
            )
        return "\n".join(lines)

    def run_query(self, query, use_llm=True):
        retrieved = self.retrieve(query)
        answer = self.generate_answer(query, retrieved, use_llm=use_llm)
        return answer, retrieved


def log_run(root, payload):
    log_path = Path(root) / "logs" / "runs.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def build_log_payload(query, answer, retrieved, prompt_id="rag_v1"):
    return {
        "timestamp": int(time.time()),
        "query": query,
        "prompt_id": prompt_id,
        "retrieved_chunks": retrieved,
        "answer": answer,
    }
