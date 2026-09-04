"""Repository and snapshot comparison helpers."""
from __future__ import annotations


def _get(stats: dict, *path, default=0):
    current = stats
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _metric(name: str, a, b, higher_is_better: bool = True) -> dict:
    try:
        delta = round(float(b) - float(a), 2)
    except (TypeError, ValueError):
        delta = None
    winner = "tie"
    if delta is not None and delta != 0:
        if (delta > 0 and higher_is_better) or (delta < 0 and not higher_is_better):
            winner = "b"
        else:
            winner = "a"
    return {"metric": name, "a": a, "b": b, "delta_b_minus_a": delta, "winner": winner}


def compare_repos(stats_a: dict, stats_b: dict) -> dict:
    metrics = [
        _metric("Health score", _get(stats_a, "health", "score"), _get(stats_b, "health", "score")),
        _metric("Stars", _get(stats_a, "repo", "stars"), _get(stats_b, "repo", "stars")),
        _metric("Forks", _get(stats_a, "repo", "forks"), _get(stats_b, "repo", "forks")),
        _metric("Commits / 90d", _get(stats_a, "activity", "commits_90d"), _get(stats_b, "activity", "commits_90d")),
        _metric("Contributors sampled", _get(stats_a, "contributors", "sampled_total"), _get(stats_b, "contributors", "sampled_total")),
        _metric("Bus factor", _get(stats_a, "contributors", "bus_factor"), _get(stats_b, "contributors", "bus_factor")),
        _metric("Issue closure %", _get(stats_a, "issues", "closure_rate_pct"), _get(stats_b, "issues", "closure_rate_pct")),
        _metric("PR merge %", _get(stats_a, "pull_requests", "merge_rate_pct"), _get(stats_b, "pull_requests", "merge_rate_pct")),
        _metric("Days since last commit", _get(stats_a, "activity", "days_since_last_commit"), _get(stats_b, "activity", "days_since_last_commit"), False),
    ]
    return {
        "repo_a": _get(stats_a, "repo", "full_name", default="A"),
        "repo_b": _get(stats_b, "repo", "full_name", default="B"),
        "metrics": metrics,
    }


def compare_snapshots(old_stats: dict, new_stats: dict) -> dict:
    result = compare_repos(old_stats, new_stats)
    result["comparison_type"] = "snapshot_drift"
    result["old"] = result.pop("repo_a")
    result["new"] = result.pop("repo_b")
    return result
