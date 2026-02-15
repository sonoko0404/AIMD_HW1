from pathlib import Path
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


def load_chunks(chunks_path):
    chunks = []
    with Path(chunks_path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks


def main():
    root = Path(__file__).resolve().parents[2]
    chunks_path = root / "data" / "processed" / "chunks.jsonl"
    if not chunks_path.exists():
        raise FileNotFoundError(str(chunks_path))
    chunks = load_chunks(chunks_path)
    texts = [c["text"] for c in chunks]
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(
        texts, batch_size=32, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True
    )
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    index_path = root / "data" / "processed" / "index.faiss"
    faiss.write_index(index, str(index_path))
    meta_path = root / "data" / "processed" / "chunks_meta.jsonl"
    with meta_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
