"""
Classifies each recruiter query into an intent.

Two-tier approach: try a quick keyword/regex match first (no LLM call at
all), and only fall back to asking the model when nothing matches. Most
of the common queries in this app ("how many applicants", "shortlist",
"help") never need to touch the LLM.
"""
import re
from enum import Enum
from llm import llm_generate_json


class Intent(str, Enum):
    LOAD_JD = "LOAD_JD"
    COUNT_APPLICANTS = "COUNT_APPLICANTS"
    TOP_CANDIDATES = "TOP_CANDIDATES"
    REWRITE_JD = "REWRITE_JD"
    INTERVIEW_QUESTIONS = "INTERVIEW_QUESTIONS"
    SALARY_EXPECTATIONS = "SALARY_EXPECTATIONS"
    COMPARE_CANDIDATES = "COMPARE_CANDIDATES"
    MISMATCH_FEEDBACK = "MISMATCH_FEEDBACK"
    JD_IMPROVEMENT = "JD_IMPROVEMENT"
    SKILL_TRENDS = "SKILL_TRENDS"
    SCHEDULE_INTERVIEW = "SCHEDULE_INTERVIEW"
    VIEW_CALENDAR = "VIEW_CALENDAR"
    RED_FLAGS = "RED_FLAGS"
    BATCH_REPORT = "BATCH_REPORT"
    DRAFT_EMAIL = "DRAFT_EMAIL"
    SHORTLIST = "SHORTLIST"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"


# order matters here - more specific phrasing needs to be checked before
# broader patterns that might also match it (e.g. "shortlist the top
# candidates" contains the word "top", so SHORTLIST has to win first)
_KEYWORD_RULES = [
    (Intent.HELP, [r"^help$", r"^\?$", r"what can you do"]),
    (Intent.COUNT_APPLICANTS, [r"\bhow many\b.*(applicant|candidate|resume)"]),
    (Intent.BATCH_REPORT, [r"\bbatch\b.*(report|screen)", r"\bscreen all\b", r"\bfull report\b"]),
    (Intent.RED_FLAGS, [r"\bred flag", r"\bemployment gap", r"\binconsistent dates?\b"]),
    (Intent.VIEW_CALENDAR, [r"\bshow\b.*(calendar|schedule)", r"\bwho'?s scheduled\b"]),
    (Intent.SCHEDULE_INTERVIEW, [r"\bschedule\b.*interview", r"\bbook\b.*(interview|slot)", r"\bset up\b.*interview"]),
    (Intent.SKILL_TRENDS, [r"\btrending skills?\b", r"\bskill trend", r"\bin.demand skills?\b", r"skills?.*trending", r"trending.*skills?"]),
    (Intent.JD_IMPROVEMENT, [r"\bimprove\b.*(jd|job description)", r"missing.*(jd|job description)", r"\bwhat'?s missing\b"]),
    (Intent.DRAFT_EMAIL, [r"\bemail\b", r"\bdraft\b.*mail"]),
    (Intent.SHORTLIST, [r"\bshortlist\b", r"\bfinalize\b"]),
    (Intent.REWRITE_JD, [r"\brewrite\b.*\bjd\b", r"\brewrite\b.*(job description|posting)"]),
    (Intent.INTERVIEW_QUESTIONS, [r"\binterview question", r"\bquestions for\b"]),
    (Intent.SALARY_EXPECTATIONS, [r"\bsalary\b", r"\bcompensation\b", r"\bpay range\b"]),
    (Intent.COMPARE_CANDIDATES, [r"\bcompare\b"]),
    (Intent.MISMATCH_FEEDBACK, [r"\bmismatch\b", r"\bfeedback on\b.*jd", r"\bjd.*realistic\b", r"jd.*match.*(applicant|pool|candidate)"]),
    (Intent.TOP_CANDIDATES, [r"\btop\b.*(candidate|applicant)", r"\bbest candidate", r"\brank"]),
]


def fast_route(query: str) -> Intent | None:
    q = query.lower().strip()
    for intent, patterns in _KEYWORD_RULES:
        for pat in patterns:
            if re.search(pat, q):
                return intent
    return None


def llm_route(query: str) -> Intent:
    prompt = f"""Classify this recruiter query into exactly one intent from this list:
{[i.value for i in Intent if i != Intent.UNKNOWN]}

Query: "{query}"

Return JSON like: {{"intent": "TOP_CANDIDATES"}}"""
    try:
        data = llm_generate_json(prompt)
        value = data.get("intent", "UNKNOWN")
        return Intent(value) if value in Intent._value2member_map_ else Intent.UNKNOWN
    except Exception:
        return Intent.UNKNOWN


def classify(query: str) -> tuple[Intent, bool]:
    """Returns (intent, used_llm) so callers can show whether the fast
    path or the LLM fallback handled a given query."""
    intent = fast_route(query)
    if intent:
        return intent, False
    return llm_route(query), True
