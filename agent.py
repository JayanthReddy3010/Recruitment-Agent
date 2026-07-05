"""
Ties everything together: router picks an intent, a handler function does
the work, state carries over between turns.

The graph here is deliberately flat (router -> one handler -> response)
instead of a long chain, since almost every recruiter query in this app is
a self-contained ask rather than a multi-step pipeline. The one place state
really matters across turns is: loading a JD invalidates the old ranking,
ranking has to happen before you can shortlist, and a shortlist has to
exist before you can email anyone.

Confirmations (shortlist, email, interview booking) don't block on input()
- they store a PendingAction on state and wait for the next message to be
a yes/no. That's what lets the exact same handler code run from main.py
(terminal) and app.py (Streamlit), where you can't pause execution
mid-function for a button click.
"""
from typing import Callable
from models import AgentState, JobDescription, Candidate, PendingAction
from router import classify, Intent
from llm import llm_generate, llm_generate_json
from vector_store import (
    load_all_candidates,
    ingest_resumes,
    count_applicants,
    query_top_candidates,
)
from tools import tavily_salary_search, tavily_skill_trend_search, send_email_mock
from redflags import check_all, check_candidate
from reports import save_report
import calendar_store
from config import JD_PATH

_YES = {"y", "yes", "confirm", "ok", "okay", "sure", "go ahead"}
_NO = {"n", "no", "cancel", "stop", "nevermind", "never mind"}


def bootstrap(state: AgentState) -> str:
    candidates = load_all_candidates()
    ingest_resumes(candidates)
    state.candidates = candidates

    with open(JD_PATH, "r", encoding="utf-8") as f:
        raw_jd = f.read()
    state.jd = _parse_jd(raw_jd)

    n_pdf = sum(1 for c in candidates if c.source == "pdf")
    n_txt = len(candidates) - n_pdf
    return (
        f"Loaded {len(candidates)} resumes ({n_txt} text, {n_pdf} PDF) and parsed "
        f"the default JD for '{state.jd.role}'.\nType 'help' to see what you can ask."
    )


def reload_candidates(state: AgentState) -> str:
    """Re-scans the resume folders and rebuilds the vector index. Used by
    the UI after new resumes get uploaded."""
    candidates = load_all_candidates()
    ingest_resumes(candidates)
    state.candidates = candidates
    state.last_ranked = []
    return f"Reloaded -- {len(candidates)} resumes on file now."


def _parse_jd(raw_text: str) -> JobDescription:
    prompt = f"""Extract structured fields from this job description.

JOB DESCRIPTION:
{raw_text}

Return JSON with exactly these keys:
role (string), required_skills (list of strings), preferred_skills (list of strings),
min_experience_years (integer), responsibilities (list of strings)."""
    data = llm_generate_json(prompt)
    return JobDescription(
        role=data.get("role", "Unknown Role"),
        required_skills=data.get("required_skills", []),
        preferred_skills=data.get("preferred_skills", []),
        min_experience_years=int(data.get("min_experience_years", 0) or 0),
        responsibilities=data.get("responsibilities", []),
        raw_text=raw_text,
    )


def apply_new_jd(state: AgentState, raw_text: str) -> str:
    """Shared by the terminal's 'load a JD' flow and the UI's file upload -
    both end up here once they have the raw JD text in hand."""
    if not raw_text.strip():
        return "No JD text received -- keeping the existing JD."
    state.jd = _parse_jd(raw_text)
    state.last_ranked = []
    return (
        f"Parsed new JD for role '{state.jd.role}'.\n"
        f"Required skills: {', '.join(state.jd.required_skills)}\n"
        f"Min experience: {state.jd.min_experience_years} years"
    )


def _resolve_candidate_from_query(state: AgentState, query: str) -> Candidate | None:
    ql = query.lower()
    for c in state.candidates:
        if c.name.lower() in ql:
            return c
    if state.last_ranked:
        return state.last_ranked[0].candidate
    return None


# ---------------------------------------------------------------------
# Pending confirmation resolution
# ---------------------------------------------------------------------

def _resolve_pending(state: AgentState, query: str) -> str | None:
    """If there's a PendingAction waiting on a yes/no, interpret this query
    as the answer. Returns None if the query wasn't a yes/no reply, in
    which case the pending action is dropped and normal routing resumes
    (so the recruiter never gets stuck if they change the subject)."""
    pa = state.pending_action
    q = query.strip().lower()

    if q in _YES:
        state.pending_action = None
        return _execute_pending(state, pa)
    if q in _NO:
        state.pending_action = None
        return f"Cancelled: {pa.description}"

    state.pending_action = None
    return None


def _execute_pending(state: AgentState, pa: PendingAction) -> str:
    if pa.kind == "shortlist":
        top_n = state.last_ranked[:3]
        state.shortlist = [sc.candidate for sc in top_n]
        names = ", ".join(c.name for c in state.shortlist)
        return f"Shortlist finalized: {names}"

    if pa.kind == "draft_email":
        subject = pa.payload["subject"]
        results = []
        for cand in state.shortlist:
            body = llm_generate(pa.payload["body_prompt"].replace("{name}", cand.name))
            results.append(send_email_mock(f"{cand.name.lower().replace(' ', '.')}@example.com", subject, body))
        return "\n".join(results)

    if pa.kind == "schedule_interview":
        date_str, time_str, name = pa.payload["date"], pa.payload["time"], pa.payload["candidate_name"]
        if calendar_store.is_slot_taken(date_str, time_str):
            return f"{date_str} {time_str} just got booked by someone else -- pick another slot."
        calendar_store.book_slot(name, date_str, time_str, note=pa.payload.get("note", ""))
        return f"Booked: {name} on {date_str} at {time_str}"

    return "Nothing to confirm."


# ---------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------

def h_load_jd(state: AgentState, query: str) -> str:
    print("Paste the new job description, then press Enter twice:")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    return apply_new_jd(state, "\n".join(lines).strip())


def h_count_applicants(state: AgentState, query: str) -> str:
    n = count_applicants()
    return f"{n} applicants currently on file. (counted directly, no LLM call used)"


def h_top_candidates(state: AgentState, query: str) -> str:
    if not state.jd:
        return "No JD loaded yet -- load one first."
    ranked = query_top_candidates(state.jd, state.candidates, k=5)
    state.last_ranked = ranked
    lines = [f"Top {len(ranked)} candidates for '{state.jd.role}':"]
    for i, sc in enumerate(ranked, 1):
        lines.append(
            f"{i}. {sc.candidate.name} -- score {sc.match_score}/100 "
            f"| matched: {', '.join(sc.matched_skills) or 'none'} "
            f"| missing: {', '.join(sc.missing_skills) or 'none'}"
        )
    return "\n".join(lines)


def h_rewrite_jd(state: AgentState, query: str) -> str:
    if not state.jd:
        return "No JD loaded yet -- load one first."
    tone_hint = "startup, energetic, concise"
    if "corporate" in query.lower():
        tone_hint = "formal, corporate"
    prompt = f"""Rewrite this job description in a {tone_hint} tone.
Keep all required skills and experience requirements accurate -- do not invent
or drop requirements.

ORIGINAL JD:
{state.jd.raw_text}"""
    return llm_generate(prompt)


def h_interview_questions(state: AgentState, query: str) -> str:
    if not state.jd:
        return "No JD loaded yet -- load one first."
    target = _resolve_candidate_from_query(state, query)
    if not target:
        return "Couldn't tell which candidate you mean -- try 'interview questions for <name>'."
    prompt = f"""Generate 6 interview questions for this candidate, grounded in
the JD's actual requirements and this candidate's specific resume gaps/strengths.
Mix technical and behavioral questions.

JD REQUIREMENTS:
{state.jd.raw_text}

CANDIDATE RESUME:
{target.raw_text}"""
    return llm_generate(prompt)


def h_salary_expectations(state: AgentState, query: str) -> str:
    role = state.jd.role if state.jd else "Software Engineer"
    return tavily_salary_search(role)


def h_skill_trends(state: AgentState, query: str) -> str:
    role = state.jd.role if state.jd else "Software Engineer"
    search_results = tavily_skill_trend_search(role)
    if not state.jd:
        return search_results
    prompt = f"""Here are live search results about in-demand skills for a {role} role:

{search_results}

Our current JD asks for these required skills: {', '.join(state.jd.required_skills)}
And these preferred skills: {', '.join(state.jd.preferred_skills)}

In 4-5 sentences, point out any trending skill the JD is missing, and whether
anything in the JD looks outdated."""
    return llm_generate(prompt)


def h_compare_candidates(state: AgentState, query: str) -> str:
    if len(state.candidates) < 2:
        return "Need at least two candidates loaded to compare."
    names_in_query = [c for c in state.candidates if c.name.lower() in query.lower()]
    pool = names_in_query if len(names_in_query) >= 2 else (
        [sc.candidate for sc in state.last_ranked[:2]] if len(state.last_ranked) >= 2 else state.candidates[:2]
    )
    a, b = pool[0], pool[1]
    prompt = f"""Compare these two candidates side by side against the JD.
Give a short table-like summary (skills overlap, experience, gaps) and a
one-line recommendation of who's the stronger fit and why.

JD:
{state.jd.raw_text if state.jd else '(no JD loaded)'}

CANDIDATE A - {a.name}:
{a.raw_text}

CANDIDATE B - {b.name}:
{b.raw_text}"""
    return llm_generate(prompt)


def h_mismatch_feedback(state: AgentState, query: str) -> str:
    if not state.jd:
        return "No JD loaded yet -- load one first."
    pool_summary = "\n".join(
        f"- {c.name}: {c.experience_years} yrs, skills: {', '.join(c.skills)}"
        for c in state.candidates
    )
    prompt = f"""You are reviewing whether a JD's requirements are realistic given
the actual applicant pool. Point out any mismatch (e.g. JD asks for N years
but most applicants have fewer, or asks for a skill almost nobody has) and
suggest a concrete adjustment. Be specific and brief (5-6 sentences max).

JD:
{state.jd.raw_text}

APPLICANT POOL:
{pool_summary}"""
    return llm_generate(prompt)


def h_jd_improvement(state: AgentState, query: str) -> str:
    if not state.jd:
        return "No JD loaded yet -- load one first."
    prompt = f"""Review this job description for missing standard fields a
good JD usually has (e.g. salary range, remote/hybrid/onsite, team size,
seniority level, growth path, tech stack detail). List what's missing and
suggest a one-line addition for each. Be concrete, not generic.

JD:
{state.jd.raw_text}"""
    return llm_generate(prompt)


def h_red_flags(state: AgentState, query: str) -> str:
    named = any(c.name.lower() in query.lower() for c in state.candidates)
    target = _resolve_candidate_from_query(state, query) if named else None

    if target:
        result = check_candidate(target)
        if not result.flags:
            return f"No red flags found for {target.name}."
        return f"Red flags for {target.name}:\n" + "\n".join(f"- {f}" for f in result.flags)

    flagged = check_all(state.candidates)
    if not flagged:
        return "No red flags found across the applicant pool."
    lines = [f"{len(flagged)} candidate(s) with red flags:"]
    for r in flagged:
        lines.append(f"- {r.candidate_name}: {'; '.join(r.flags)}")
    return "\n".join(lines)


def h_batch_report(state: AgentState, query: str) -> str:
    if not state.jd:
        return "No JD loaded yet -- load one first."
    path = save_report(state.jd, state.candidates)
    return f"Batch report generated for all {len(state.candidates)} candidates -> {path}"


def h_schedule_interview(state: AgentState, query: str) -> str:
    target = _resolve_candidate_from_query(state, query)
    if not target:
        return "Couldn't tell which candidate you mean -- include their name."

    prompt = f"""Extract a date and time for an interview from this request.
Return JSON: {{"date": "YYYY-MM-DD", "time": "HH:MM"}}. If no date/time is
mentioned, use null for both.

Request: "{query}" """
    try:
        data = llm_generate_json(prompt)
        date_str, time_str = data.get("date"), data.get("time")
    except Exception:
        date_str, time_str = None, None

    if not date_str or not time_str:
        return "Couldn't figure out the date/time -- try something like 'schedule an interview with Priya for 2026-07-10 at 14:00'."

    if calendar_store.is_slot_taken(date_str, time_str):
        return f"{date_str} {time_str} is already booked -- pick another slot."

    role = state.jd.role if state.jd else "role"
    state.pending_action = PendingAction(
        kind="schedule_interview",
        description=f"Book {target.name} for {date_str} at {time_str}?",
        payload={"candidate_name": target.name, "date": date_str, "time": time_str, "note": f"Interview for {role}"},
    )
    return f"{state.pending_action.description} (reply 'yes' to confirm or 'no' to cancel)"


def h_view_calendar(state: AgentState, query: str) -> str:
    slots = calendar_store.list_slots()
    if not slots:
        return "No interviews scheduled yet."
    lines = ["Scheduled interviews:"]
    for s in sorted(slots, key=lambda s: (s.date, s.time)):
        lines.append(f"- {s.date} {s.time}: {s.candidate_name} ({s.note})")
    return "\n".join(lines)


def h_shortlist(state: AgentState, query: str) -> str:
    if not state.last_ranked:
        return "Run 'get me top candidates' first so there's a ranking to shortlist from."
    top_n = state.last_ranked[:3]
    names = ", ".join(sc.candidate.name for sc in top_n)
    state.pending_action = PendingAction(kind="shortlist", description=f"Finalize shortlist as: {names}?")
    return f"{state.pending_action.description} (reply 'yes' to confirm or 'no' to cancel)"


def h_draft_email(state: AgentState, query: str) -> str:
    if not state.shortlist:
        return "No shortlist yet -- finalize a shortlist first ('shortlist top candidates')."
    subject = f"Interview invitation -- {state.jd.role if state.jd else 'open role'}"
    body_prompt = (
        f"Write a short, warm interview-invitation email for a candidate named "
        f"{{name}} applying for {state.jd.role if state.jd else 'the role'}. 3-4 sentences, "
        f"professional tone, mentions next steps will follow."
    )
    preview = llm_generate(body_prompt.replace("{name}", state.shortlist[0].name))
    state.pending_action = PendingAction(
        kind="draft_email",
        description=f"Send this email to all {len(state.shortlist)} shortlisted candidates?",
        payload={"subject": subject, "body_prompt": body_prompt},
    )
    return (
        f"--- DRAFT EMAIL PREVIEW (to {state.shortlist[0].name}) ---\n{preview}\n\n"
        f"{state.pending_action.description} (reply 'yes' to send or 'no' to cancel)"
    )


def h_help(state: AgentState, query: str) -> str:
    return """You can ask things like:
  - "load a new JD"
  - "how many applicants do we have?"
  - "get me the top candidates"
  - "rewrite this JD for a startup"
  - "interview questions for <candidate name>"
  - "what are salary expectations for this role?"
  - "what skills are trending for this role?"
  - "what's missing from this JD?"
  - "compare <name A> and <name B>"
  - "does the JD match our applicant pool?" (mismatch feedback)
  - "any red flags?" or "red flags for <name>"
  - "run a batch report"
  - "schedule an interview with <name> for <date> at <time>"
  - "show the calendar"
  - "shortlist the top candidates"
  - "draft and send an email to the shortlist"
  - "exit" to quit"""


def h_unknown(state: AgentState, query: str) -> str:
    return "I'm not sure what you're asking -- type 'help' to see supported queries."


_HANDLERS: dict[Intent, Callable[[AgentState, str], str]] = {
    Intent.LOAD_JD: h_load_jd,
    Intent.COUNT_APPLICANTS: h_count_applicants,
    Intent.TOP_CANDIDATES: h_top_candidates,
    Intent.REWRITE_JD: h_rewrite_jd,
    Intent.INTERVIEW_QUESTIONS: h_interview_questions,
    Intent.SALARY_EXPECTATIONS: h_salary_expectations,
    Intent.SKILL_TRENDS: h_skill_trends,
    Intent.COMPARE_CANDIDATES: h_compare_candidates,
    Intent.MISMATCH_FEEDBACK: h_mismatch_feedback,
    Intent.JD_IMPROVEMENT: h_jd_improvement,
    Intent.RED_FLAGS: h_red_flags,
    Intent.BATCH_REPORT: h_batch_report,
    Intent.SCHEDULE_INTERVIEW: h_schedule_interview,
    Intent.VIEW_CALENDAR: h_view_calendar,
    Intent.SHORTLIST: h_shortlist,
    Intent.DRAFT_EMAIL: h_draft_email,
    Intent.HELP: h_help,
    Intent.UNKNOWN: h_unknown,
}


def handle(state: AgentState, query: str) -> str:
    state.turn_count += 1

    if state.pending_action:
        resolved = _resolve_pending(state, query)
        if resolved is not None:
            return resolved
        # not a yes/no reply -- pending action was dropped, fall through
        # and treat this message as a fresh query

    intent, used_llm = classify(query)
    tag = "[router: LLM fallback]" if used_llm else "[router: keyword match, no LLM]"
    handler = _HANDLERS.get(intent, h_unknown)
    result = handler(state, query)
    return f"{tag} intent={intent.value}\n{result}"
