from repo_scope.profile import RepoProfile


REPO = {
    "full_name": "acme/demo",
    "name": "demo",
    "description": "Demo repo",
    "html_url": "https://github.com/acme/demo",
    "owner": {"login": "acme"},
    "default_branch": "main",
    "visibility": "public",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2026-09-01T00:00:00Z",
    "pushed_at": "2026-09-01T00:00:00Z",
    "stargazers_count": 100,
    "forks_count": 12,
    "watchers_count": 3,
    "size": 400,
    "topics": ["python"],
    "archived": False,
    "fork": False,
    "license": {"spdx_id": "MIT"},
}
COMMITS = [{"commit": {"committer": {"date": "2026-09-01T00:00:00Z"}}}]
CONTRIBUTORS = [{"login": "a", "contributions": 60}, {"login": "b", "contributions": 40}]
ISSUES = [{"state": "closed", "created_at": "2026-08-01T00:00:00Z", "closed_at": "2026-08-02T00:00:00Z"}]
PULLS = [{"state": "closed", "merged_at": "2026-08-03T00:00:00Z"}]


def test_profile_orchestration(monkeypatch):
    from repo_scope.fetch import github_api

    monkeypatch.setattr(github_api, "get_repo_info", lambda *a, **k: REPO)
    monkeypatch.setattr(github_api, "get_commits", lambda *a, **k: COMMITS)
    monkeypatch.setattr(github_api, "get_contributors", lambda *a, **k: CONTRIBUTORS)
    monkeypatch.setattr(github_api, "get_issues", lambda *a, **k: ISSUES)
    monkeypatch.setattr(github_api, "get_pull_requests", lambda *a, **k: PULLS)
    monkeypatch.setattr(github_api, "get_languages", lambda *a, **k: {"Python": 800, "HTML": 200})
    monkeypatch.setattr(github_api, "get_repository_paths", lambda *a, **k: ["README.md", ".github/workflows/ci.yml", "tests/test_app.py", "CONTRIBUTING.md"])

    profile = RepoProfile("acme/demo")
    payload = profile.to_dict()
    assert payload["stats"]["repo"]["full_name"] == "acme/demo"
    assert payload["stats"]["contributors"]["bus_factor"] == 1
    assert payload["stats"]["signals"]["has_ci"] is True
    assert payload["stats"]["health"]["score"] > 0


def test_profile_rejects_invalid_slug():
    import pytest
    with pytest.raises(ValueError):
        RepoProfile("owner/repo?x=1")
