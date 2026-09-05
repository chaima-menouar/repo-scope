from pathlib import Path

from fastapi.testclient import TestClient

from repo_scope.insights import build_structured_diagnosis
from repo_scope.report.renderer import render_html, render_json
from repo_scope.web import app


class FakeProfile:
    def to_dict(self):
        return {
            "generated_at": "2026-09-04T00:00:00Z",
            "stats": {
                "repo": {"full_name": "acme/demo", "description": "demo", "stars": 10, "forks": 2, "topics": []},
                "health": {"score": 80, "label": "Healthy"},
                "activity": {"commits_90d": 10, "sampled_commits": 20, "days_since_last_commit": 2},
                "contributors": {"bus_factor": 3},
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
    assert response.json()["version"] == "0.6.0"


def test_structured_diagnosis_is_explainable():
    diagnosis = build_structured_diagnosis(
        {
            "stats": {
                "health": {"score": 45, "label": "Needs attention"},
                "activity": {"days_since_last_commit": 100},
                "contributors": {"bus_factor": 1},
                "issues": {"closure_rate_pct": 35},
                "pull_requests": {"merge_rate_pct": 40},
                "signals": {"has_ci": False, "has_tests": False},
            }
        }
    )
    assert diagnosis["risk_level"] == "high"
    assert diagnosis["top_risks"]
    assert diagnosis["next_actions"]
    assert all(item["evidence"] for item in diagnosis["top_risks"])
