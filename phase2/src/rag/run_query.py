import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.rag.engine import RAGEngine, log_run, build_log_payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--use-llm", action="store_true")
    args = parser.parse_args()
    engine = RAGEngine(top_k=args.top_k)
    answer, retrieved = engine.run_query(args.query, use_llm=args.use_llm)
    payload = build_log_payload(args.query, answer, retrieved)
    log_run(engine.root, payload)
    print(answer)


if __name__ == "__main__":
    main()
