from __future__ import annotations

from repo_scope.fetch import github_api


class _Response:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = ""
        self.links = {}

    def json(self):
        return {"ok": True}


def test_rate_limit_wait_uses_reset_header(monkeypatch):
    monkeypatch.setattr(github_api.time, "time", lambda: 1000)
    response = _Response(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1060"})
    assert github_api._rate_limit_wait_seconds(response) == 65


def test_request_waits_once_and_retries_when_batch_wait_is_enabled(monkeypatch):
    responses = [
        _Response(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1060"}),
        _Response(200),
    ]
    sleeps: list[int] = []

    monkeypatch.setattr(github_api.time, "time", lambda: 1000)
    monkeypatch.setattr(github_api.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(github_api.requests, "get", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(github_api, "GITHUB_RATE_LIMIT_WAIT_MAX_SECONDS", 900)

    response = github_api._request("/repos/example/project")
    assert response.status_code == 200
    assert sleeps == [65]


def test_request_does_not_wait_in_fail_fast_mode(monkeypatch):
    response = _Response(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1060"})
    monkeypatch.setattr(github_api.time, "time", lambda: 1000)
    monkeypatch.setattr(github_api.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(github_api, "GITHUB_RATE_LIMIT_WAIT_MAX_SECONDS", 0)

    try:
        github_api._request("/repos/example/project")
    except github_api.GitHubAPIError as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("fail-fast mode should raise on rate limit")
