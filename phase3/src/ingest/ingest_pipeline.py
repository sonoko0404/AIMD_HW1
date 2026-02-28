from pathlib import Path
import csv
import json
import re
from pypdf import PdfReader


def normalize_text(text):
    text = text.replace("\u00ad", "")
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def read_pdf(path):
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def chunk_text(text, chunk_size=1000, overlap=150):
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        raw_end = min(start + chunk_size, length)
        left = start
        if start > 0:
            while left > 0 and not text[left - 1].isspace():
                left -= 1
        right = raw_end
        if raw_end < length:
            while right < length and not text[right].isspace():
                right += 1
        chunk = text[left:right].strip()
        if chunk:
            chunks.append(chunk)
        if raw_end == length:
            break
        start = raw_end - overlap
    return chunks


def main():
    root = Path(__file__).resolve().parents[2]
    manifest_path = root / "data" / "data_manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(str(manifest_path))
    with manifest_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    processed_manifest_rows = []
    chunks = []
    for record in rows:
        raw_path_value = str(record.get("raw_path", "")).strip()
        if not raw_path_value:
            continue
        raw_path = Path(raw_path_value)
        if not raw_path.is_absolute():
            raw_path = root / raw_path
        if not raw_path.exists():
            continue
        suffix = raw_path.suffix.lower()
        if suffix == ".pdf":
            text = read_pdf(raw_path)
        elif suffix in [".txt", ".md"]:
            text = read_text(raw_path)
        else:
            continue
        text = normalize_text(text)
        processed_rel = Path("data") / "processed" / f"{record['source_id']}.txt"
        processed_path = root / processed_rel
        processed_path.write_text(text, encoding="utf-8")
        record["processed_path"] = processed_rel.as_posix()
        processed_manifest_rows.append(record)
        for idx, chunk in enumerate(chunk_text(text)):
            chunk_id = f"{record['source_id']}_chunk_{idx:04d}"
            chunks.append(
                {
                    "source_id": record["source_id"],
                    "chunk_id": chunk_id,
                    "text": chunk,
                }
            )
    processed_manifest_path = root / "data" / "processed" / "processed_manifest.csv"
    if processed_manifest_rows:
        with processed_manifest_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=processed_manifest_rows[0].keys())
            writer.writeheader()
            writer.writerows(processed_manifest_rows)
    chunks_path = root / "data" / "processed" / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
