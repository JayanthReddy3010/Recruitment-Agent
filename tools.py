"""
External tools - things the LLM shouldn't try to answer from memory or
can't do computation for on its own.
"""
from datetime import datetime
from config import TAVILY_API_KEY, SENT_EMAIL_LOG


def _tavily_search(query: str, max_results: int = 5) -> list[dict]:
    if not TAVILY_API_KEY:
        return []
    from tavily import TavilyClient
    client = TavilyClient(api_key=TAVILY_API_KEY)
    result = client.search(query=query, max_results=max_results, search_depth="basic")
    return result.get("results", [])


def tavily_salary_search(role: str, location: str = "India") -> str:
    results = _tavily_search(f"{role} average salary {location} 2026")
    if not results:
        return (
            "[TAVILY_API_KEY not set -- add one to .env for live results] "
            f"Fallback: check levels.fyi or Glassdoor manually for {role} salaries in {location}."
        )
    lines = [f"- {r.get('title')}: {r.get('content', '')[:220]} ({r.get('url')})" for r in results]
    return "\n".join(lines)


def tavily_skill_trend_search(role: str) -> str:
    results = _tavily_search(f"most in-demand skills for {role} 2026")
    if not results:
        return "[TAVILY_API_KEY not set -- add one to .env for live results]"
    lines = [f"- {r.get('title')}: {r.get('content', '')[:220]} ({r.get('url')})" for r in results]
    return "\n".join(lines)


def send_email_mock(to: str, subject: str, body: str) -> str:
    """No real SMTP/Gmail wiring for hackathon day - the important part is
    the agent drafting the right email and asking before it "sends". Logged
    to a file so it's provable it happened."""
    entry = (
        f"\n--- EMAIL SENT {datetime.now().isoformat(timespec='seconds')} ---\n"
        f"To: {to}\nSubject: {subject}\n\n{body}\n"
    )
    with open(SENT_EMAIL_LOG, "a", encoding="utf-8") as f:
        f.write(entry)
    return f"Email sent to {to} (logged to {SENT_EMAIL_LOG})"
