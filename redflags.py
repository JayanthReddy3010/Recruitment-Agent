"""
Looks for problems in a candidate's employment history that a human
screener would want flagged before an interview:
  - gaps longer than 5 months between two jobs
  - overlapping date ranges (two "current" jobs at once, etc.)
  - stated experience_years that doesn't roughly match the history

All date math, no LLM involved - these are facts you can check, not
something that needs a language model's judgment.
"""
from datetime import date
from models import Candidate, RedFlag, EmploymentEntry

GAP_THRESHOLD_MONTHS = 5


def _to_month_index(value: str) -> int:
    """'2021-06' -> 2021*12+6, '2021' -> 2021*12+1, 'present' -> today."""
    value = value.strip().lower()
    if value == "present":
        today = date.today()
        return today.year * 12 + today.month
    parts = value.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    return year * 12 + month


def _months_between(a: int, b: int) -> int:
    return b - a


def check_candidate(candidate: Candidate) -> RedFlag:
    flags = []
    history = candidate.employment_history

    if not history:
        return RedFlag(candidate_id=candidate.id, candidate_name=candidate.name, flags=[])

    # sort by start date so gap/overlap checks read left to right
    parsed = []
    for entry in history:
        try:
            parsed.append((entry, _to_month_index(entry.start), _to_month_index(entry.end)))
        except (ValueError, IndexError):
            continue
    parsed.sort(key=lambda t: t[1])

    for i in range(len(parsed) - 1):
        _, _, end_a = parsed[i]
        entry_b, start_b, _ = parsed[i + 1]
        gap = _months_between(end_a, start_b)
        if gap > GAP_THRESHOLD_MONTHS:
            flags.append(
                f"{gap}-month gap before joining {entry_b.company} "
                f"({parsed[i][0].end} to {entry_b.start})"
            )
        elif gap < 0:
            flags.append(
                f"overlapping employment: {parsed[i][0].company} and "
                f"{entry_b.company} both active around {entry_b.start}"
            )

    total_months = sum(end - start for _, start, end in parsed)
    stated_months = candidate.experience_years * 12
    if stated_months and abs(total_months - stated_months) > 12:
        flags.append(
            f"stated experience ({candidate.experience_years} yrs) doesn't line up "
            f"with employment history (~{round(total_months / 12, 1)} yrs)"
        )

    return RedFlag(candidate_id=candidate.id, candidate_name=candidate.name, flags=flags)


def check_all(candidates: list[Candidate]) -> list[RedFlag]:
    results = [check_candidate(c) for c in candidates]
    return [r for r in results if r.flags]
