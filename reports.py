"""
Runs every candidate against the JD in one pass and writes a report to
disk. Reuses the same RAG scoring as "top candidates" (query_top_candidates
with k = all of them) rather than re-implementing scoring logic twice.
"""
import os
from datetime import datetime
from config import REPORTS_DIR
from models import JobDescription, Candidate
from vector_store import query_top_candidates
from redflags import check_all


def build_report(jd: JobDescription, candidates: list[Candidate]) -> str:
    ranked = query_top_candidates(jd, candidates, k=len(candidates))
    flags_by_id = {f.candidate_id: f.flags for f in check_all(candidates)}

    lines = [
        f"Batch Screening Report -- {jd.role}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Candidates screened: {len(candidates)}",
        "=" * 70,
    ]
    for i, sc in enumerate(ranked, 1):
        lines.append(f"\n{i}. {sc.candidate.name}  (score: {sc.match_score}/100)")
        lines.append(f"   Experience: {sc.candidate.experience_years} yrs | Education: {sc.candidate.education}")
        lines.append(f"   Matched skills: {', '.join(sc.matched_skills) or 'none'}")
        lines.append(f"   Missing skills: {', '.join(sc.missing_skills) or 'none'}")
        cflags = flags_by_id.get(sc.candidate.id, [])
        if cflags:
            lines.append(f"   Red flags: {'; '.join(cflags)}")

    return "\n".join(lines)


def save_report(jd: JobDescription, candidates: list[Candidate]) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_text = build_report(jd, candidates)
    filename = f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = os.path.join(REPORTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report_text)
    return path
