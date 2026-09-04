"""Explainable repository health and bus-factor scoring."""
from __future__ import annotations


def bus_factor(contributors: list[dict], threshold: float = 0.5) -> int:
    """Return how many top contributors are needed to reach ``threshold`` of commits."""
    contributions = sorted((max(0, int(c.get("contributions", 0))) for c in contributors), reverse=True)
    total = sum(contributions)
    if total <= 0:
        return 0
    target = total * min(max(threshold, 0.01), 1.0)
    running = 0
    for idx, value in enumerate(contributions, start=1):
        running += value
        if running >= target:
            return idx
    return len(contributions)


def _activity_score(days: int | None) -> float:
    if days is None:
        return 8
    if days <= 7:
        return 30
    if days <= 30:
        return 26
    if days <= 90:
        return 19
    if days <= 180:
        return 11
    if days <= 365:
        return 5
    return 1


def _resilience_score(factor: int, contributor_count: int) -> float:
    if contributor_count <= 1:
        return 4
    if factor >= 5:
        return 20
    if factor == 4:
        return 18
    if factor == 3:
        return 15
    if factor == 2:
        return 10
    return 5


def compute_health_score(stats: dict, alerts: list | None = None) -> int:
    """Compute a transparent 0-100 score from repository metrics."""
    factor = int(stats.get("contributors", {}).get("bus_factor", 0))
    contributor_count = int(stats.get("contributors", {}).get("sampled_total", 0))
    days = stats.get("activity", {}).get("days_since_last_commit")

    issue_rate = stats.get("issues", {}).get("closure_rate_pct")
    issue_score = 9 if issue_rate is None else max(0, min(15, issue_rate / 100 * 15))

    pr_rate = stats.get("pull_requests", {}).get("merge_rate_pct")
    pr_score = 6 if pr_rate is None else max(0, min(10, pr_rate / 100 * 10))

    signals = stats.get("signals", {})
    practice_score = (
        5 * bool(signals.get("has_ci"))
        + 5 * bool(signals.get("has_tests"))
        + 3 * bool(signals.get("has_license"))
        + 3 * bool(signals.get("has_contributing"))
        + 4 * bool(signals.get("has_readme"))
    )

    community_score = 5
    if stats.get("issues", {}).get("stale_open_90d", 0) > 25:
        community_score = 2
    elif stats.get("issues", {}).get("stale_open_90d", 0) > 5:
        community_score = 3.5

    score = (
        _activity_score(days)
        + _resilience_score(factor, contributor_count)
        + issue_score
        + pr_score
        + practice_score
        + community_score
    )

    if stats.get("repo", {}).get("archived"):
        score = min(score, 35)
    return int(round(max(0, min(100, score))))


def health_label(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Healthy"
    if score >= 55:
        return "Watch"
    if score >= 40:
        return "Risky"
    return "Critical"
