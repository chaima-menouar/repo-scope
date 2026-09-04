"""Time-series aggregation for repository activity."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _bucket(dt: datetime, granularity: str) -> str:
    if granularity == "week":
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"
    return dt.strftime("%Y-%m")


def commits_over_time(commits: list[dict], granularity: str = "month") -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for item in commits:
        inner = item.get("commit", {})
        dt = _parse(inner.get("committer", {}).get("date") or inner.get("author", {}).get("date"))
        if dt:
            counts[_bucket(dt, granularity)] += 1
    return [{"date": key, "count": counts[key]} for key in sorted(counts)]


def issues_opened_vs_closed(issues: list[dict], granularity: str = "month") -> list[dict]:
    rows: dict[str, dict[str, int]] = defaultdict(lambda: {"opened": 0, "closed": 0})
    for issue in issues:
        created = _parse(issue.get("created_at"))
        closed = _parse(issue.get("closed_at"))
        if created:
            rows[_bucket(created, granularity)]["opened"] += 1
        if closed:
            rows[_bucket(closed, granularity)]["closed"] += 1
    return [
        {"date": key, "opened": rows[key]["opened"], "closed": rows[key]["closed"]}
        for key in sorted(rows)
    ]
