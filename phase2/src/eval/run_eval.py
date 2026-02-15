import json
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.rag.engine import RAGEngine, build_log_payload, log_run


def load_queries(path):
    queries = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))
    return queries


def extract_cited_chunk_ids(text):
    pattern = r"\(([^,]+),\s*([^)]+)\)"
    return [m.group(2).strip() for m in re.finditer(pattern, text)]


def main():
    root = Path(__file__).resolve().parents[2]
    query_path = root / "data" / "eval" / "queries.jsonl"
    queries = load_queries(query_path)
    engine = RAGEngine()
    results_path = root / "outputs" / "eval_results.jsonl"
    summary_path = root / "outputs" / "eval_summary.json"
    all_coverages = []
    all_evidence_counts = []
    with results_path.open("w", encoding="utf-8") as out_f:
        for q in queries:
            query_text = q["query"]
            answer, retrieved = engine.run_query(query_text, use_llm=True)
            cited = extract_cited_chunk_ids(answer)
            evidence_count = len(retrieved)
            coverage = len(set(cited)) / max(1, evidence_count)
            all_coverages.append(coverage)
            all_evidence_counts.append(evidence_count)
            result = {
                "query_id": q.get("query_id"),
                "query": query_text,
                "type": q.get("type"),
                "answer": answer,
                "retrieved_chunks": retrieved,
                "citation_coverage": coverage,
                "evidence_count": evidence_count,
            }
            out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
            log_run(engine.root, build_log_payload(query_text, answer, retrieved, prompt_id="rag_eval_v1"))
    summary = {
        "num_queries": len(queries),
        "avg_citation_coverage": float(sum(all_coverages) / max(1, len(all_coverages))),
        "avg_evidence_count": float(sum(all_evidence_counts) / max(1, len(all_evidence_counts))),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
