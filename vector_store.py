"""
RAG layer over resumes using ChromaDB.

The JD's wording and a resume's wording rarely match exactly ("built REST
APIs" vs "designed backend services"), so semantic search over embeddings
finds fits that plain keyword matching would miss. Uses Chroma's default
local embedding model (all-MiniLM-L6-v2) so we don't need a second API key
just for embeddings.
"""
import os
import re
import glob
import chromadb
from config import RESUME_DIR, PDF_RESUME_DIR, CHROMA_PERSIST_DIR
from models import Candidate, ScoredCandidate, JobDescription, EmploymentEntry

_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_COLLECTION_NAME = "resumes"


def _grab_field(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.lower().startswith(field.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def _parse_employment_block(text: str) -> list[EmploymentEntry]:
    """Looks for a block like:

        Employment History:
        2019-06 to 2021-08: InfoEdge Technologies
        2021-09 to present: CloudNova Systems

    and turns it into structured entries for the red-flag checker.
    """
    lines = text.splitlines()
    entries = []
    in_block = False
    for line in lines:
        if line.strip().lower() == "employment history:":
            in_block = True
            continue
        if in_block:
            if not line.strip():
                break
            m = re.match(r"\s*([\d]{4}(?:-\d{2})?)\s+to\s+(present|[\d]{4}(?:-\d{2})?)\s*:\s*(.+)", line, re.I)
            if m:
                start, end, company = m.groups()
                entries.append(EmploymentEntry(company=company.strip(), start=start, end=end.lower()))
            else:
                break
    return entries


def _parse_resume_file(path: str) -> Candidate:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    name = _grab_field(text, "Name") or os.path.basename(path)
    skills_raw = _grab_field(text, "Skills")
    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    exp_raw = _grab_field(text, "Experience")
    exp_years = 0
    for tok in exp_raw.split():
        if tok.isdigit():
            exp_years = int(tok)
            break
    education = _grab_field(text, "Education")

    return Candidate(
        id=os.path.splitext(os.path.basename(path))[0],
        name=name,
        skills=skills,
        experience_years=exp_years,
        education=education,
        raw_text=text,
        source="txt",
        employment_history=_parse_employment_block(text),
    )


def load_all_candidates() -> list[Candidate]:
    """Loads every txt resume plus every PDF resume, keyed by filename id."""
    txt_paths = sorted(glob.glob(os.path.join(RESUME_DIR, "*.txt")))
    candidates = [_parse_resume_file(p) for p in txt_paths]

    from pdf_utils import load_all_pdf_candidates
    pdf_candidates = load_all_pdf_candidates(PDF_RESUME_DIR)
    for c in pdf_candidates:
        c.employment_history = _parse_employment_block(c.raw_text)
    candidates.extend(pdf_candidates)

    return candidates


def count_applicants() -> int:
    """Pure Python, no LLM call involved -- counting doesn't need one."""
    n_txt = len(glob.glob(os.path.join(RESUME_DIR, "*.txt")))
    n_pdf = len(glob.glob(os.path.join(PDF_RESUME_DIR, "*.pdf"))) if os.path.isdir(PDF_RESUME_DIR) else 0
    return n_txt + n_pdf


def ingest_resumes(candidates: list[Candidate]) -> None:
    try:
        _client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass
    collection = _client.create_collection(_COLLECTION_NAME)
    collection.add(
        ids=[c.id for c in candidates],
        documents=[c.raw_text for c in candidates],
        metadatas=[{"name": c.name, "experience_years": c.experience_years} for c in candidates],
    )


def _distance_to_score(distance: float) -> float:
    similarity = max(0.0, 1 - (distance / 2))
    return round(similarity * 100, 1)


def query_top_candidates(jd: JobDescription, candidates: list[Candidate], k: int = 5) -> list[ScoredCandidate]:
    collection = _client.get_collection(_COLLECTION_NAME)
    query_text = (
        f"Role: {jd.role}. Required skills: {', '.join(jd.required_skills)}. "
        f"Preferred skills: {', '.join(jd.preferred_skills)}. "
        f"Minimum experience: {jd.min_experience_years} years."
    )
    results = collection.query(query_texts=[query_text], n_results=min(k, len(candidates)))

    by_id = {c.id: c for c in candidates}
    scored = []
    for cid, dist in zip(results["ids"][0], results["distances"][0]):
        cand = by_id[cid]
        req_lower = {s.lower() for s in jd.required_skills}
        cand_lower = {s.lower() for s in cand.skills}
        matched = sorted(s for s in cand.skills if s.lower() in req_lower)
        missing = sorted(s for s in jd.required_skills if s.lower() not in cand_lower)
        scored.append(
            ScoredCandidate(
                candidate=cand,
                match_score=_distance_to_score(dist),
                matched_skills=matched,
                missing_skills=missing,
            )
        )
    scored.sort(key=lambda s: s.match_score, reverse=True)
    return scored
