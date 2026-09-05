"""FastAPI application used by the RepoScope web dashboard."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from repo_scope.analysis.compare import compare_repos
from repo_scope.fetch.github_api import GitHubAPIError
from repo_scope.insights import generate_ai_insight
from repo_scope.profile import RepoProfile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = PROJECT_ROOT / "public"

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


def _profile(repo: str, refresh: bool) -> RepoProfile:
    try:
        return RepoProfile(repo, use_cache=not refresh)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        status = 404 if exc.status_code == 404 else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc


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


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(PUBLIC_DIR / "index.html")


if (PUBLIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=PUBLIC_DIR / "assets"), name="assets")
