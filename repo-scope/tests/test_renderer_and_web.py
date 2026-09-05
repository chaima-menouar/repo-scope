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


def test_human_validation_dashboard_and_status_are_available():
    client = TestClient(app)
    page = client.get("/validation")
    assert page.status_code == 200
    assert "Human Validation" in page.text

    status = client.get("/api/human-validation/status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["queue_repositories"] >= 0
    assert payload["raw_decisions"] >= 0
    assert "write_enabled" in payload
    assert "readiness" in payload


def test_human_validation_candidate_view_hides_automation_fields():
    client = TestClient(app)
    response = client.get("/api/human-validation/candidates", params={"reviewer": "reviewer-test", "limit": 1})
    assert response.status_code in {200, 409}
    if response.status_code == 200 and response.json()["candidates"]:
        candidate = response.json()["candidates"][0]
        assert "review_reason" not in candidate
        assert "weak_label" not in candidate
        assert "predicted_label" not in candidate
        assert "confidence" not in candidate
        assert "health_score" not in candidate


def test_human_review_write_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("REPOSCOPE_HUMAN_REVIEW_WRITE_ENABLED", raising=False)
    client = TestClient(app)
    response = client.post(
        "/api/human-validation/review",
        json={
            "repo": "org/example",
            "reviewer": "reviewer-test",
            "human_label": "healthy",
            "review_notes": "Evidence-based notes for a disabled write test.",
        },
    )
    assert response.status_code == 403


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
