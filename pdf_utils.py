"""
Real PDF resume parsing. Text-format resumes have a predictable header
we can regex out (Name:, Skills:, etc). PDFs won't always be that clean
once they're actual scanned/exported resumes, but since our sample PDFs
were generated from the same header format, we reuse the txt parser's
regex logic first and only fall back to the LLM if that comes back empty.
"""
import os
import glob
from pypdf import PdfReader
from models import Candidate


def extract_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _grab_field(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.lower().startswith(field.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def parse_pdf_resume(path: str) -> Candidate:
    text = extract_pdf_text(path)
    cid = os.path.splitext(os.path.basename(path))[0]

    name = _grab_field(text, "Name")
    skills_raw = _grab_field(text, "Skills")
    education = _grab_field(text, "Education")
    exp_raw = _grab_field(text, "Experience")

    if name and skills_raw:
        # header-style PDF, same as our txt resumes - parse directly, no LLM needed
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
        exp_years = 0
        for tok in exp_raw.split():
            if tok.isdigit():
                exp_years = int(tok)
                break
        return Candidate(
            id=cid, name=name, skills=skills, experience_years=exp_years,
            education=education, raw_text=text, source="pdf",
        )

    # fallback for unstructured/real-world PDFs: ask the model to extract fields
    from llm import llm_generate_json
    prompt = f"""Extract these fields from the resume text below as JSON:
name, skills (list of strings), experience_years (integer), education (string).

RESUME TEXT:
{text[:4000]}"""
    data = llm_generate_json(prompt)
    return Candidate(
        id=cid,
        name=data.get("name", cid),
        skills=data.get("skills", []),
        experience_years=int(data.get("experience_years", 0) or 0),
        education=data.get("education", ""),
        raw_text=text,
        source="pdf",
    )


def load_all_pdf_candidates(pdf_dir: str) -> list[Candidate]:
    if not os.path.isdir(pdf_dir):
        return []
    paths = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    return [parse_pdf_resume(p) for p in paths]
