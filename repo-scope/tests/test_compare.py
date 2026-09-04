from repo_scope.analysis.compare import compare_repos


def test_compare_repos():
    a = {"repo": {"full_name": "a/a", "stars": 1, "forks": 2}, "health": {"score": 70}, "activity": {"commits_90d": 10, "days_since_last_commit": 4}, "contributors": {"sampled_total": 3, "bus_factor": 1}, "issues": {"closure_rate_pct": 50}, "pull_requests": {"merge_rate_pct": 60}}
    b = {"repo": {"full_name": "b/b", "stars": 3, "forks": 2}, "health": {"score": 80}, "activity": {"commits_90d": 20, "days_since_last_commit": 1}, "contributors": {"sampled_total": 5, "bus_factor": 2}, "issues": {"closure_rate_pct": 70}, "pull_requests": {"merge_rate_pct": 75}}
    result = compare_repos(a, b)
    assert result["repo_a"] == "a/a"
    assert result["repo_b"] == "b/b"
    assert result["metrics"][0]["winner"] == "b"
