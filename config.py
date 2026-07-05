"""
Central config: loads API keys from .env and sets up the Gemini client.
Keeping this in one place means the rest of the codebase never touches
os.environ directly -- makes swapping providers later a one-file change.
"""
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

GEMINI_MODEL = "Gemini 2.5 Flash"   # separate quota bucket from gemini-2.5-flash;
# gemini-2.5-flash's free tier on this account is only 20 requests/day (confirmed by
# Google's own 429 error, not the often-quoted ~1,500/day figure -- Google has tightened
# free-tier quotas several times in 2026 and actual limits vary by account/region).
# Check your real limit anytime at https://aistudio.google.com/usage

RESUME_DIR = os.path.join(os.path.dirname(__file__), "data", "resumes")
PDF_RESUME_DIR = os.path.join(os.path.dirname(__file__), "data", "resumes_pdf")
JD_PATH = os.path.join(os.path.dirname(__file__), "data", "job_description.txt")
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_store")
SENT_EMAIL_LOG = os.path.join(os.path.dirname(__file__), "sent_emails.log")
CALENDAR_FILE = os.path.join(os.path.dirname(__file__), "data", "calendar.json")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")

if not GEMINI_API_KEY:
    print("[WARN] GEMINI_API_KEY not set. Add it to a .env file (see .env.example).")
if not TAVILY_API_KEY:
    print("[WARN] TAVILY_API_KEY not set. Salary search will use a fallback message.")
