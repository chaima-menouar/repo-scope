from pathlib import Path

from fastapi.testclient import TestClient

from repo_scope.report.renderer import render_html, render_json
from repo_scope.web import app


class FakeProfile:
    def to_dict(self):
        return {
            "generated_at": "2026-09-04T00:00:00Z",
            "stats": {
                "repo": {"full_name": "acme/demo", "description": "demo", "stars": 10, "forks": 2, "topics": []},
                "health": {"score": 80, "label": "Healthy"},
                "activity": {"commits_90d": 10, "sampled_commits": 20},
                "contributors": {"bus_factor": 2},
                "issues": {"closure_rate_pct": 70},
                "pull_requests": {"merge_rate_pct": 75},
                "signals": {"has_ci": True, "has_tests": True},
                "languages": [{"name": "Python", "percent": 100}],
            },
            "alerts": [{"level": "info", "message": "Looks good", "code": "ok"}],
            "timeseries": {
                "commits": [{"date": "2026-09", "count": 10}],
                "issues": [{"date": "2026-09", "opened": 2, "closed": 3}],
            },
            "smart_summary": "Healthy repository.",
        }


def test_renderer_outputs_files(tmp_path: Path):
    html = tmp_path / "report.html"
    js = tmp_path / "report.json"
    render_html(FakeProfile(), str(html))
    render_json(FakeProfile(), str(js))
    assert "RepoScope" in html.read_text()
    assert '"generated_at"' in js.read_text()


def test_web_shell_and_health():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
