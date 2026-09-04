from repo_scope.analysis.alerts import generate_alerts
from repo_scope.analysis.health import bus_factor, compute_health_score
from repo_scope.analysis.timeseries import commits_over_time, issues_opened_vs_closed


def test_bus_factor_counts_majority():
    contributors = [
        {"contributions": 50},
        {"contributions": 30},
        {"contributions": 20},
    ]
    assert bus_factor(contributors) == 1
    assert bus_factor([{"contributions": 40}, {"contributions": 35}, {"contributions": 25}], 0.7) == 2


def test_health_score_and_alerts():
    stats = {
        "repo": {"archived": False},
        "activity": {"days_since_last_commit": 3},
        "contributors": {"bus_factor": 3, "sampled_total": 12},
        "issues": {"closure_rate_pct": 80.0, "sampled_total": 50, "stale_open_90d": 1},
        "pull_requests": {"merge_rate_pct": 90.0},
        "signals": {"has_ci": True, "has_tests": True, "has_license": True, "has_contributing": True, "has_readme": True},
    }
    alerts = generate_alerts(stats)
    score = compute_health_score(stats, alerts)
    assert score >= 80
    assert not any(a.level == "critical" for a in alerts)


def test_time_series_buckets():
    commits = [
        {"commit": {"committer": {"date": "2026-01-05T10:00:00Z"}}},
        {"commit": {"committer": {"date": "2026-01-20T10:00:00Z"}}},
        {"commit": {"committer": {"date": "2026-02-01T10:00:00Z"}}},
    ]
    assert commits_over_time(commits) == [
        {"date": "2026-01", "count": 2},
        {"date": "2026-02", "count": 1},
    ]
    issues = [{"created_at": "2026-01-01T00:00:00Z", "closed_at": "2026-02-01T00:00:00Z"}]
    assert issues_opened_vs_closed(issues) == [
        {"date": "2026-01", "opened": 1, "closed": 0},
        {"date": "2026-02", "opened": 0, "closed": 1},
    ]
