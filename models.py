from pydantic import BaseModel, Field
from typing import List, Optional


class JobDescription(BaseModel):
    role: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    min_experience_years: int = 0
    responsibilities: List[str] = Field(default_factory=list)
    raw_text: str = ""


class EmploymentEntry(BaseModel):
    company: str = ""
    start: str = ""   # "YYYY-MM" or "YYYY"
    end: str = ""      # "YYYY-MM", "YYYY", or "present"


class Candidate(BaseModel):
    id: str
    name: str
    skills: List[str] = Field(default_factory=list)
    experience_years: int = 0
    education: str = ""
    raw_text: str = ""
    source: str = "txt"   # "txt" or "pdf"
    employment_history: List[EmploymentEntry] = Field(default_factory=list)


class ScoredCandidate(BaseModel):
    candidate: Candidate
    match_score: float
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)


class RedFlag(BaseModel):
    candidate_id: str
    candidate_name: str
    flags: List[str] = Field(default_factory=list)


class InterviewSlot(BaseModel):
    candidate_name: str
    date: str    # "YYYY-MM-DD"
    time: str    # "HH:MM"
    note: str = ""


class PendingAction(BaseModel):
    """A proposed action awaiting a yes/no from the recruiter. Storing this
    in state (instead of blocking on input()) is what makes the same
    handler code work from both the terminal and the Streamlit UI, where
    you can't pause mid-function for a button click."""
    kind: str  # "shortlist" | "draft_email" | "schedule_interview"
    description: str
    payload: dict = Field(default_factory=dict)


class AgentState(BaseModel):
    jd: Optional[JobDescription] = None
    candidates: List[Candidate] = Field(default_factory=list)
    last_ranked: List[ScoredCandidate] = Field(default_factory=list)
    shortlist: List[Candidate] = Field(default_factory=list)
    pending_action: Optional[PendingAction] = None
    turn_count: int = 0

    class Config:
        arbitrary_types_allowed = True
