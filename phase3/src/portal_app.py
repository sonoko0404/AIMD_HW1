import csv
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv, dotenv_values
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.rag.engine import RAGEngine, build_log_payload, log_run


ROOT = Path(__file__).resolve().parents[1]


def apply_api_config():
    env_path = ROOT / ".env"
    env_values = dotenv_values(env_path) if env_path.exists() else {}
    load_dotenv(env_path, override=False)
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    source = "environment" if key else "none"
    if "OPENAI_API_KEY" in env_values:
        source = ".env"
    try:
        secrets = st.secrets
        secret_key = secrets.get("OPENAI_API_KEY")
        secret_model = secrets.get("OPENAI_MODEL")
    except FileNotFoundError:
        secret_key = None
        secret_model = None
    except Exception:
        secret_key = None
        secret_model = None
    if secret_key:
        os.environ["OPENAI_API_KEY"] = secret_key
        key = secret_key
        source = "streamlit_secrets"
    if secret_model:
        os.environ["OPENAI_MODEL"] = secret_model
        model = secret_model
        source = "streamlit_secrets"
    return key, model, source


@st.cache_resource
def get_engine(top_k):
    return RAGEngine(top_k=top_k)


@st.cache_data
def load_manifest():
    manifest_path = ROOT / "data" / "data_manifest.csv"
    if not manifest_path.exists():
        return {}
    with manifest_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["source_id"]: row for row in reader}


def ensure_dirs():
    (ROOT / "outputs" / "exports").mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs" / "artifacts").mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs").mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)


def source_label(source_id, manifest):
    item = manifest.get(source_id, {})
    title = item.get("title", source_id)
    year = item.get("year", "")
    url = item.get("url_or_doi", "")
    parts = [title]
    if year:
        parts.append(str(year))
    label = " - ".join(parts)
    if url:
        return f"{label} ({url})"
    return label


def extract_first_sentence(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[0] if parts else text.strip()


def select_claim_sentence(text, query):
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    query_terms = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
    best = ""
    best_score = -1
    for sent in sentences:
        cleaned = sent.strip()
        if len(cleaned) < 40 or len(cleaned) > 240:
            continue
        tokens = re.findall(r"[a-zA-Z0-9]+", cleaned.lower())
        if len(tokens) < 8:
            continue
        score = 0
        if query_terms:
            score += 3 * len(query_terms & set(tokens))
        if any(ch.isdigit() for ch in cleaned):
            score += 1
        if any(word in cleaned.lower() for word in ["result", "evidence", "improve", "increase", "decrease", "effect", "impact", "find", "shows", "suggests"]):
            score += 1
        if score > best_score:
            best = cleaned
            best_score = score
    if best:
        return best
    for sent in sentences:
        cleaned = sent.strip()
        if len(cleaned) >= 20:
            return cleaned
    return extract_first_sentence(text)


def generate_claim_llm(text, query, api_key, model):
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        context = truncate_text(text, 1200)
        prompt = (
            "Given the passage, write one sentence claim strictly grounded in the passage. "
            "Do not add new facts. Use wording from the passage when possible. "
            "If the passage is mostly metadata or bibliography, return a short topic phrase from the passage.\n\n"
            f"Question: {query}\n\nPassage:\n{context}\n\nClaim:"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        claim = resp.choices[0].message.content.strip()
        if not claim:
            return None
        claim = extract_first_sentence(claim)
        claim_tokens = set(re.findall(r"[a-zA-Z0-9]+", claim.lower()))
        passage_tokens = set(re.findall(r"[a-zA-Z0-9]+", context.lower()))
        if claim_tokens and passage_tokens:
            overlap = len(claim_tokens & passage_tokens) / max(1, len(claim_tokens))
            if overlap < 0.5:
                return None
        return truncate_text(claim, 240)
    except Exception:
        return None


def truncate_text(text, limit):
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    clipped = cleaned[:limit].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip()
    return clipped


def build_evidence_rows(query, retrieved, use_llm=False, api_key=None, model="gpt-4o-mini"):
    rows = []
    for item in retrieved:
        raw_text = item.get("text", "")
        snippet = truncate_text(raw_text, 280)
        llm_claim = None
        if use_llm and api_key:
            llm_claim = generate_claim_llm(raw_text, query, api_key, model)
        claim = llm_claim or select_claim_sentence(raw_text, query) or f"Evidence relevant to: {query}"
        citation = f"({item.get('source_id')}, {item.get('chunk_id')})"
        confidence = item.get("rerank_score", item.get("score", 0.0))
        rows.append(
            {
                "Claim": claim,
                "Evidence snippet": snippet,
                "Citation": citation,
                "Confidence": round(float(confidence), 3),
                "Notes": "Heuristic claim from retrieved chunk",
            }
        )
    return rows


def rows_to_markdown(rows, manifest):
    headers = ["Claim", "Evidence snippet", "Citation", "Confidence", "Notes"]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        values = []
        for h in headers:
            value = str(row.get(h, "")).replace("\n", " ").replace("|", "\\|")
            values.append(value)
        lines.append("| " + " | ".join(values) + " |")
    source_ids = []
    for row in rows:
        match = re.search(r"\(([^,]+),", row.get("Citation", ""))
        if match:
            source_ids.append(match.group(1).strip())
    unique_ids = []
    for sid in source_ids:
        if sid not in unique_ids:
            unique_ids.append(sid)
    if unique_ids:
        lines.append("\nReferences")
        for sid in unique_ids:
            lines.append(f"- {source_label(sid, manifest)}")
    return "\n".join(lines)


def rows_to_csv(rows):
    output = io.StringIO()
    fieldnames = ["Claim", "Evidence snippet", "Citation", "Confidence", "Notes"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def build_pdf_bytes(text):
    buffer = io.BytesIO()
    page_width, page_height = letter
    pdf = canvas.Canvas(buffer, pagesize=letter)
    left = inch
    right = page_width - inch
    y = page_height - inch
    line_height = 14
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            y -= line_height
            if y < inch:
                pdf.showPage()
                y = page_height - inch
            continue
        while line:
            fit = line
            while pdf.stringWidth(fit, "Helvetica", 10) > (right - left) and len(fit) > 1:
                fit = fit[:-1]
            pdf.setFont("Helvetica", 10)
            pdf.drawString(left, y, fit)
            y -= line_height
            if y < inch:
                pdf.showPage()
                y = page_height - inch
            line = line[len(fit):].lstrip()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def save_artifact(rows, manifest):
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_text = rows_to_csv(rows)
    md_text = rows_to_markdown(rows, manifest)
    pdf_bytes = build_pdf_bytes(md_text)
    csv_path = ROOT / "outputs" / "exports" / f"evidence_table_{timestamp}.csv"
    md_path = ROOT / "outputs" / "exports" / f"evidence_table_{timestamp}.md"
    pdf_path = ROOT / "outputs" / "exports" / f"evidence_table_{timestamp}.pdf"
    csv_path.write_text(csv_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    pdf_path.write_bytes(pdf_bytes)
    return csv_text, md_text, pdf_bytes, csv_path, md_path, pdf_path


def save_thread(entry):
    ensure_dirs()
    path = ROOT / "outputs" / "threads.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def run_eval_portal(engine, use_llm):
    ensure_dirs()
    query_path = ROOT / "data" / "eval" / "queries.jsonl"
    if not query_path.exists():
        return None, None, []
    results_path = ROOT / "outputs" / "eval_results_portal.jsonl"
    summary_path = ROOT / "outputs" / "eval_summary_portal.json"
    queries = []
    with query_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))
    all_coverages = []
    all_evidence_counts = []
    examples = []
    with results_path.open("w", encoding="utf-8") as out_f:
        for q in queries:
            query_text = q.get("query", "")
            answer, retrieved = engine.run_query(query_text, use_llm=use_llm)
            cited = re.findall(r"\(([^,]+),\s*([^)]+)\)", answer)
            cited_ids = [c[1].strip() for c in cited]
            evidence_count = len(retrieved)
            coverage = len(set(cited_ids)) / max(1, evidence_count)
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
            log_run(engine.root, build_log_payload(query_text, answer, retrieved, prompt_id="portal_eval_v1"))
            if len(examples) < 3:
                examples.append(result)
    summary = {
        "num_queries": len(queries),
        "avg_citation_coverage": float(sum(all_coverages) / max(1, len(all_coverages))),
        "avg_evidence_count": float(sum(all_evidence_counts) / max(1, len(all_evidence_counts))),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary, results_path, examples


st.set_page_config(page_title="Personal Research Portal", layout="wide")
st.title("Personal Research Portal")

api_key_value, llm_model_value, api_key_source = apply_api_config()

manifest = load_manifest()

if "history" not in st.session_state:
    st.session_state["history"] = []
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "last_eval_summary" not in st.session_state:
    st.session_state["last_eval_summary"] = None

with st.sidebar:
    st.header("Settings")
    top_k = st.slider("Top-k evidence", min_value=3, max_value=10, value=5, step=1)
    use_llm = st.checkbox("Use LLM for answers", value=True)
    st.caption("LLM requires OPENAI_API_KEY")
    st.caption(f"OPENAI_API_KEY detected: {bool(api_key_value)}")
    st.caption(f"LLM model: {llm_model_value}")
    st.caption(f"API key source: {api_key_source}")

    if st.button("Test API Connection"):
        if not api_key_value:
            st.error("No API Key provided.")
        else:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key_value)
                client.models.list()
                st.success(f"API Connection Successful! (Key: {api_key_value[:8]}...)")
            except Exception as e:
                st.error(f"API Connection Failed: {e}")

tabs = st.tabs(["Ask", "Search", "Artifacts", "Evaluation", "History"])

with tabs[0]:
    st.subheader("Ask a research question")
    query = st.text_area("Question", placeholder="e.g., What evidence links AI to improved supply chain performance?")
    if st.button("Run answer", type="primary"):
        if query.strip():
            engine = get_engine(top_k)
            answer, retrieved = engine.run_query(query, use_llm=use_llm)
            if use_llm:
                if engine.last_used_llm:
                    st.success(f"LLM used: {engine.last_llm_model}")
                elif engine.last_llm_error:
                    st.warning(f"LLM not used: {engine.last_llm_error}")
                else:
                    st.warning("LLM not used.")
            payload = build_log_payload(query, answer, retrieved, prompt_id="portal_ask_v1")
            log_run(engine.root, payload)
            entry = {
                "timestamp": int(time.time()),
                "query": query,
                "answer": answer,
                "retrieved_chunks": retrieved,
            }
            st.session_state["history"].insert(0, entry)
            st.session_state["last_result"] = entry
        else:
            st.warning("Please enter a question.")
    if st.session_state["last_result"]:
        last = st.session_state["last_result"]
        st.markdown("**Answer**")
        st.write(last["answer"])
        st.markdown("**Evidence**")
        for item in last["retrieved_chunks"]:
            snippet = truncate_text(item.get("text", ""), 320)
            source_id = item.get("source_id")
            chunk_id = item.get("chunk_id")
            st.write(f"{snippet} ({source_id}, {chunk_id})")
            st.caption(source_label(source_id, manifest))
        if st.button("Save thread to disk"):
            path = save_thread(last)
            st.success(f"Saved to {path.as_posix()}")

with tabs[1]:
    st.subheader("Search evidence")
    search_query = st.text_area("Search query", key="search_query")
    if st.button("Search"):
        if search_query.strip():
            engine = get_engine(top_k)
            retrieved = engine.retrieve(search_query)
            st.markdown("**Top evidence**")
            for item in retrieved:
                snippet = truncate_text(item.get("text", ""), 320)
                source_id = item.get("source_id")
                chunk_id = item.get("chunk_id")
                st.write(f"{snippet} ({source_id}, {chunk_id})")
                st.caption(source_label(source_id, manifest))
        else:
            st.warning("Please enter a search query.")

with tabs[2]:
    st.subheader("Evidence table artifact")
    current = st.session_state.get("last_result")
    if not current:
        st.info("Run a question in Ask to generate an evidence table.")
    else:
        rows = build_evidence_rows(
            current["query"],
            current["retrieved_chunks"],
            use_llm=use_llm,
            api_key=api_key_value,
            model=llm_model_value,
        )
        st.dataframe(rows, use_container_width=True)
        if st.button("Export evidence table"):
            csv_text, md_text, pdf_bytes, csv_path, md_path, pdf_path = save_artifact(rows, manifest)
            st.success("Artifact saved.")
            st.download_button("Download CSV", data=csv_text, file_name=csv_path.name, mime="text/csv")
            st.download_button("Download Markdown", data=md_text, file_name=md_path.name, mime="text/markdown")
            st.download_button("Download PDF", data=pdf_bytes, file_name=pdf_path.name, mime="application/pdf")

with tabs[3]:
    st.subheader("Evaluation")
    st.write("Run the evaluation set and summarize citation coverage.")
    if st.button("Run evaluation"):
        engine = get_engine(top_k)
        summary, results_path, examples = run_eval_portal(engine, use_llm=use_llm)
        if summary:
            st.session_state["last_eval_summary"] = summary
            st.json(summary)
            st.write("Examples")
            for ex in examples:
                st.write(ex["query"])
                st.write(ex["answer"])
        else:
            st.warning("Evaluation queries not found.")
    summary_path = ROOT / "outputs" / "eval_summary_portal.json"
    if summary_path.exists() and not st.session_state.get("last_eval_summary"):
        st.caption(f"Latest summary: {summary_path.as_posix()}")
        st.json(json.loads(summary_path.read_text(encoding="utf-8")))

with tabs[4]:
    st.subheader("History")
    history = st.session_state.get("history", [])
    if not history:
        st.info("No history yet.")
    else:
        for entry in history:
            ts = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"**{ts}**")
            st.write(entry["query"])
            st.write(entry["answer"])
            st.divider()
        if st.button("Export history"):
            ensure_dirs()
            export_path = ROOT / "outputs" / "history.jsonl"
            with export_path.open("w", encoding="utf-8") as f:
                for entry in history:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            st.success(f"Saved to {export_path.as_posix()}")
