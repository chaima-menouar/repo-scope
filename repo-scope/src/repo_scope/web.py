"""FastAPI application used by the RepoScope web dashboard."""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from repo_scope.analysis.compare import compare_repos
from repo_scope.fetch.github_api import GitHubAPIError
from repo_scope.insights import generate_ai_insight
from repo_scope.profile import RepoProfile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = PROJECT_ROOT / "public"
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
QUEUE_PATH = DATA_DIR / "repo_risk_human_review_queue.csv"
DECISIONS_PATH = DATA_DIR / "repo_risk_human_review_decisions.csv"
ASSIGNMENTS_PATH = DATA_DIR / "repo_risk_human_review_assignments.csv"
HUMAN_LABELS_PATH = DATA_DIR / "repo_risk_human_labels.csv"
AGREEMENT_PATH = DATA_DIR / "repo_risk_human_reviewer_agreement.json"
ADJUDICATION_PATH = DATA_DIR / "repo_risk_human_adjudication.json"
PROGRESS_PATH = DATA_DIR / "repo_risk_100k_progress.json"
READINESS_PATH = MODELS_DIR / "repo_risk_100k_readiness.json"
REVIEW_LOCK = threading.Lock()
REVIEWER_RE = re.compile(r"^[A-Za-z0-9._-]{2,64}$")
ALLOWED_REVIEW_LABELS = {"healthy", "watch", "risky"}
SAFE_REVIEW_FIELDS = [
    "repo",
    "snapshot_at_utc",
    "language",
    "stars",
    "size_kb",
    "catalog_pushed_at",
    "archived",
    "latest_release_age_days",
    "latest_release_at",
]
DECISION_COLUMNS = ["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"]

app = FastAPI(
    title="RepoScope API",
    version="0.6.0",
    description="Repository intelligence: GitHub health, risk, activity, comparison and AI-assisted insights.",
)


class AnalyzeRequest(BaseModel):
    repo: str = Field(..., examples=["fastapi/fastapi"])
    refresh: bool = False


class CompareRequest(BaseModel):
    repo_a: str = Field(..., examples=["fastapi/fastapi"])
    repo_b: str = Field(..., examples=["pallets/flask"])
    refresh: bool = False


class HumanReviewRequest(BaseModel):
    repo: str
    reviewer: str
    human_label: str
    review_notes: str = Field(..., min_length=8, max_length=2000)


def _profile(repo: str, refresh: bool) -> RepoProfile:
    try:
        return RepoProfile(repo, use_cache=not refresh)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        status = 404 if exc.status_code == 404 else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc


def _read_json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _validate_reviewer(reviewer: str) -> str:
    reviewer = reviewer.strip()
    if not REVIEWER_RE.fullmatch(reviewer):
        raise HTTPException(
            status_code=422,
            detail="Reviewer ID must be 2-64 characters using letters, numbers, dot, underscore or dash.",
        )
    return reviewer


def _assigned_repos(reviewer: str) -> set[str] | None:
    if not ASSIGNMENTS_PATH.exists():
        return None
    assigned = {
        (row.get("repo") or "").strip()
        for row in _read_csv(ASSIGNMENTS_PATH)
        if (row.get("reviewer") or "").strip() == reviewer and (row.get("repo") or "").strip()
    }
    if not assigned:
        raise HTTPException(status_code=409, detail=f"No review assignment exists for reviewer {reviewer}.")
    return assigned


def _write_enabled() -> bool:
    return os.getenv("REPOSCOPE_HUMAN_REVIEW_WRITE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "repo-scope", "version": "0.6.0"}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    return _profile(request.repo, request.refresh).to_dict()


@app.post("/api/compare")
def compare(request: CompareRequest) -> dict:
    a = _profile(request.repo_a, request.refresh)
    b = _profile(request.repo_b, request.refresh)
    return {
        "comparison": compare_repos(a.stats, b.stats),
        "a": a.to_dict(),
        "b": b.to_dict(),
    }


@app.post("/api/ai-insight")
def ai_insight(request: AnalyzeRequest) -> dict:
    profile = _profile(request.repo, request.refresh)
    return generate_ai_insight(profile.to_dict())


@app.get("/api/human-validation/status")
def human_validation_status() -> dict:
    queue = [row for row in _read_csv(QUEUE_PATH) if (row.get("repo") or "").strip()]
    decisions = [row for row in _read_csv(DECISIONS_PATH) if (row.get("repo") or "").strip()]
    labels = [row for row in _read_csv(HUMAN_LABELS_PATH) if (row.get("repo") or "").strip()]
    reviewers = sorted({(row.get("reviewer") or "").strip() for row in decisions if (row.get("reviewer") or "").strip()})
    return {
        "queue_repositories": len({row["repo"].strip() for row in queue}),
        "raw_decisions": len(decisions),
        "reviewed_repositories": len({(row.get("repo") or "").strip() for row in decisions}),
        "reviewers": reviewers,
        "reviewer_count": len(reviewers),
        "adjudicated_repositories": len({(row.get("repo") or "").strip() for row in labels}),
        "assignments_configured": ASSIGNMENTS_PATH.exists(),
        "write_enabled": _write_enabled(),
        "progress": _read_json(PROGRESS_PATH),
        "agreement": _read_json(AGREEMENT_PATH),
        "adjudication": _read_json(ADJUDICATION_PATH),
        "readiness": _read_json(READINESS_PATH),
    }


@app.get("/api/human-validation/candidates")
def human_validation_candidates(
    reviewer: str = Query(..., min_length=2, max_length=64),
    limit: int = Query(1, ge=1, le=25),
) -> dict:
    reviewer = _validate_reviewer(reviewer)
    assigned = _assigned_repos(reviewer)
    reviewed = {
        (row.get("repo") or "").strip()
        for row in _read_csv(DECISIONS_PATH)
        if (row.get("reviewer") or "").strip() == reviewer
    }
    candidates = []
    for row in _read_csv(QUEUE_PATH):
        repo = (row.get("repo") or "").strip()
        if not repo or repo in reviewed or (assigned is not None and repo not in assigned):
            continue
        candidates.append({field: (row.get(field) or "").strip() for field in SAFE_REVIEW_FIELDS})
        if len(candidates) >= limit:
            break
    return {
        "reviewer": reviewer,
        "assignment_mode": "assigned" if assigned is not None else "open_queue",
        "candidates": candidates,
        "remaining_visible": len(candidates),
    }


@app.post("/api/human-validation/review")
def submit_human_review(request: HumanReviewRequest) -> dict:
    if not _write_enabled():
        raise HTTPException(
            status_code=403,
            detail="Human-review writes are disabled. Set REPOSCOPE_HUMAN_REVIEW_WRITE_ENABLED=true for local review sessions.",
        )
    reviewer = _validate_reviewer(request.reviewer)
    repo = request.repo.strip()
    label = request.human_label.strip().lower()
    notes = request.review_notes.strip()
    if label not in ALLOWED_REVIEW_LABELS:
        raise HTTPException(status_code=422, detail="Label must be healthy, watch or risky.")
    if not repo:
        raise HTTPException(status_code=422, detail="Repository is required.")
    queue_repos = {(row.get("repo") or "").strip() for row in _read_csv(QUEUE_PATH)}
    if repo not in queue_repos:
        raise HTTPException(status_code=404, detail="Repository is not present in the human-review queue.")
    assigned = _assigned_repos(reviewer)
    if assigned is not None and repo not in assigned:
        raise HTTPException(status_code=403, detail="Repository is not assigned to this reviewer.")

    with REVIEW_LOCK:
        rows = _read_csv(DECISIONS_PATH)
        if any(
            (row.get("repo") or "").strip() == repo and (row.get("reviewer") or "").strip() == reviewer
            for row in rows
        ):
            raise HTTPException(status_code=409, detail="This reviewer already submitted a decision for this repository.")
        decision = {
            "repo": repo,
            "human_label": label,
            "review_notes": notes,
            "reviewer": reviewer,
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        rows.append(decision)
        DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp_path = DECISIONS_PATH.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=DECISION_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        temp_path.replace(DECISIONS_PATH)
    return {"status": "saved", "decision": decision}


@app.post("/api/human-validation/refresh")
def refresh_human_validation() -> dict:
    if not _write_enabled():
        raise HTTPException(
            status_code=403,
            detail="Human-review writes are disabled. Enable local review writes before refreshing validation artifacts.",
        )
    scripts = [
        "report_reviewer_agreement.py",
        "adjudicate_human_reviews.py",
        "merge_human_labels.py",
        "compare_human_weak_labels.py",
        "evaluate_model_readiness.py",
    ]
    results = []
    for script in scripts:
        completed = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / script)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        results.append({"script": script, "returncode": completed.returncode})
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "validation refresh failed")[-2000:]
            raise HTTPException(status_code=500, detail=f"{script} failed: {detail}")
    return {"status": "refreshed", "steps": results, "validation": human_validation_status()}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(PUBLIC_DIR / "index.html")


@app.get("/validation", include_in_schema=False)
def validation_page():
    return FileResponse(PUBLIC_DIR / "validation.html")


if (PUBLIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=PUBLIC_DIR / "assets"), name="assets")
