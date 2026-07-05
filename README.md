# Recruitment System Chatbot

An agent that helps an HR recruiter go from a JD + resumes to a confirmed
shortlist, scheduled interviews, and a screening report -- available both
as a terminal app and a Streamlit chat UI, sharing the exact same logic.

## 1. Setup

```bash
# create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# get free API keys (no credit card needed for either):
#   Gemini:  https://aistudio.google.com/apikey
#   Tavily:  https://tavily.com

# copy the env template and fill in your keys
cp .env.example .env
# then edit .env -> GEMINI_API_KEY=..., TAVILY_API_KEY=...
```

First run downloads a small (~80MB) local embedding model for resume
search -- needs internet, one time only. Do this before you're on stage.

If you want the 2 sample PDF resumes regenerated (they're already included,
this is only needed if you delete them):
```bash
python3 generate_sample_pdfs.py
```

## 2. Running it

**Terminal:**
```bash
python3 main.py
```

**Browser UI:**
```bash
streamlit run app.py
```
Opens at `http://localhost:8501`. Same agent, same router, same handlers --
`app.py` is a thin UI wrapper around `agent.py`, nothing is reimplemented.

## 3. What's included

**Core (works from either interface):**
- JD upload/paste -> parsed into structured fields (role, skills, experience) via Pydantic
- 18 sample resumes (16 `.txt`, 2 real `.pdf`) with a mix of strong, partial, and weak matches
- "How many applicants?" -> plain Python count, zero LLM calls
- "Get me top candidates" -> RAG ranking over resumes with match scores
- "Rewrite this JD" / "Interview questions for X" -> LLM generation grounded in the JD + resume
- "Salary expectations?" -> live Tavily web search, not RAG
- Shortlisting and sending emails require an explicit yes/no confirmation before anything happens

**Extra features:**
- JD-vs-applicant-pool mismatch feedback ("JD asks for 5 years, most applicants have 2-3")
- Side-by-side candidate comparison
- JD improvement suggestions (missing salary range, remote policy, etc.)
- Mock interview scheduling with double-booking prevention
- Skill trend analysis (live search + comparison against the JD)
- Resume red-flag detection: employment gaps, overlapping dates, experience mismatches -- pure date math, no LLM
- Batch screening report for every candidate in one pass, saved to `reports/`
- Real PDF resume parsing (`pdf_utils.py`), not just text files
- Streamlit UI with resume/JD upload, quick-action buttons, and a live candidates table

## 4. Demo script

1. `how many applicants do we have?` -- deterministic count, no LLM call
2. `get me the top candidates` -- RAG ranking with scores
3. `rewrite this JD for a startup` -- pure LLM generation
4. `what are salary expectations for this role?` -- live web search
5. `any red flags in the applicant pool?` -- catches the 3 planted issues (a gap, an overlap, and an experience mismatch)
6. `shortlist the top candidates` -> reply `yes` -- human-in-the-loop confirmation
7. `schedule an interview with <name> for 2026-07-10 at 14:00` -> reply `yes`

Type `help` any time for the full command list.

## 5. Project layout

```
recruitment-agent/
├── main.py              # terminal entry point
├── app.py               # Streamlit UI (wraps agent.py, no separate logic)
├── agent.py             # router dispatch, handlers, pending-confirmation state machine
├── router.py            # keyword-first / LLM-fallback intent classifier
├── llm.py               # Gemini API wrapper
├── vector_store.py      # ChromaDB RAG over resumes, employment-history parsing
├── pdf_utils.py         # PDF resume text extraction + field parsing
├── redflags.py          # employment gap / overlap / mismatch detection
├── calendar_store.py    # mock interview calendar (JSON-backed, double-booking safe)
├── reports.py           # batch screening report generator
├── tools.py             # Tavily search + mock email sending
├── models.py            # Pydantic schemas
├── config.py            # env/config constants
├── generate_sample_pdfs.py
├── data/
│   ├── job_description.txt
│   ├── resumes/          # 16 text resumes
│   └── resumes_pdf/      # 2 real PDF resumes
├── requirements.txt
└── .env.example
```

## 6. Design notes

- **Routing:** keyword/regex matching is tried first for every query; the
  LLM is only asked to classify intent when nothing matches. The response
  is tagged with which path handled it, so it's visible in real time.
- **Confirmations:** shortlisting, sending emails, and booking interviews
  don't block on `input()`. They store a pending action on state and wait
  for the next message to be a yes/no -- this is what lets the same
  handler code run in the terminal and in Streamlit, where you can't pause
  mid-function for a button click.
- **Red flags are math, not opinion:** gap/overlap detection is plain date
  arithmetic on parsed employment history, deliberately not an LLM
  judgment call.
- **Left out on purpose:** real Gmail/SMTP wiring (drafts are logged
  instead of sent, since that's what changes what's actually being
  demonstrated) and OCR for scanned PDFs (our PDFs are text-based).

## 7. About the free-tier quota

Google's Gemini free tier has been tightened more than once in 2026, and
the actual per-model daily limit varies by account -- don't trust any
number you read in a blog post, including earlier claims made about this
project. Check your live limit at **https://aistudio.google.com/usage**.

This project uses `gemini-2.5-flash-lite` (set in `config.py`), a separate
model from `gemini-2.5-flash` with its own quota bucket, and is generally
the more generous of the two on the free tier. `llm.py` also retries
automatically on a transient 429 using the delay Google's own error
response suggests, and raises a clear message instead of a stack trace if
the quota is genuinely exhausted for the day.

If you hit a hard wall during the hackathon:
- Wait for the daily quota to reset (midnight Pacific time, not 24h from when you started).
- Switch `GEMINI_MODEL` in `config.py` to a different model name -- separate bucket, separate quota.
- Get a second free API key from a different Google account -- limits are per-project.
- Enable billing on the project for higher limits (a small trial credit is often included).

