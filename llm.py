"""
Thin wrapper around Google Gemini so the rest of the code just calls
llm_generate(prompt) or llm_generate_json(prompt) and doesn't care about
SDK details.

Free-tier quota is tight and can vary a lot by account (Google has
tightened it more than once this year) -- a single burst of clicking
around the demo can trip a 429. _call_with_retry retries transient ones
using the delay Google itself suggests, and raises something readable
once retries are exhausted instead of a wall of SDK traceback.
"""
import json
import re
import time
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL

_client = None
_MAX_RETRIES = 2


def _get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to a .env file (see .env.example)."
            )
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _extract_retry_delay(error_text: str) -> float:
    """Google's 429 body includes a suggested wait, e.g. "'retryDelay': '48s'"."""
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", error_text)
    return float(match.group(1)) if match else 5.0


def _call_with_retry(prompt: str) -> str:
    last_error = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = _get_client().models.generate_content(model=GEMINI_MODEL, contents=prompt)
            return response.text or ""
        except Exception as e:
            msg = str(e)
            last_error = e
            if "429" not in msg and "RESOURCE_EXHAUSTED" not in msg:
                raise  # not a rate-limit issue, don't swallow it
            if attempt < _MAX_RETRIES:
                time.sleep(min(_extract_retry_delay(msg), 60))
            else:
                raise RuntimeError(
                    "Gemini free-tier quota hit (429). Your project's daily/per-minute "
                    "limit for this model is exhausted -- check the live number at "
                    "https://aistudio.google.com/usage. Options: wait for the quota to "
                    "reset, switch GEMINI_MODEL in config.py to a different model (separate "
                    "quota bucket), or enable billing for higher limits."
                ) from e
    raise last_error  # unreachable, keeps type checkers happy


def llm_generate(prompt: str) -> str:
    """Plain text generation. Used for JD rewrite, interview questions,
    mismatch feedback, comparisons, email drafts, etc."""
    return _call_with_retry(prompt).strip()


def llm_generate_json(prompt: str) -> dict:
    """
    Ask the model for JSON only, then parse it. Used for:
    - parsing a raw JD into structured fields
    - the fallback intent classifier in router.py
    Strips markdown code fences defensively since models sometimes add them
    despite instructions.
    """
    full_prompt = (
        prompt
        + "\n\nRespond with ONLY valid JSON. No markdown, no code fences, no preamble."
    )
    raw = _call_with_retry(full_prompt) or "{}"
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise
