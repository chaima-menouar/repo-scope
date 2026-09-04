# RepoScope

**Repository intelligence for GitHub engineering teams.** RepoScope transforms recent GitHub activity into an explainable repository health profile: activity, contributor concentration, issue/PR hygiene, engineering-practice signals, alerts, trends, comparisons and optional AI-assisted recommendations.

## What ships in v0.5.0

- FastAPI web application and REST API
- Responsive dark engineering dashboard
- GitHub REST API client with authentication, pagination, caching and rate-limit errors
- Explainable 0–100 repository health score
- Bus-factor / contributor concentration analysis
- Issue and pull-request hygiene metrics
- CI, tests, README, license, contributing and security-policy detection
- Monthly commit and issue time series
- Repository comparison
- Standalone HTML and JSON reports
- CLI package (`repo-scope owner/repo`)
- Optional OpenAI-powered analyst with a deterministic fallback
- Honest supervised ML training pipeline for a future repository-risk classifier
- Pytest + Ruff CI
- Docker, Vercel and Render deployment readiness

## Architecture

```text
Browser / CLI
     |
     v
 FastAPI / RepoProfile
     |
     +--> GitHub REST API --> TTL JSON cache
     |
     +--> Analytics
     |      |- stats
     |      |- health score
     |      |- bus factor
     |      |- alerts
     |      `- time series / comparison
     |
     +--> Smart summary / optional LLM analyst
     |
     `--> Dashboard / HTML report / JSON
```

## Local run

Requires Python 3.12+.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` and API docs at `http://127.0.0.1:8000/docs`.

### Environment variables

`GITHUB_TOKEN` is strongly recommended. Public unauthenticated GitHub REST calls have a much smaller rate limit. `OPENAI_API_KEY` is optional; without it RepoScope keeps the AI panel usable with its local explainable summary.

```env
GITHUB_TOKEN=github_pat_...
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-luna
CACHE_TTL_SECONDS=3600
GITHUB_MAX_PAGES=3
```

Never commit `.env`.

## CLI

```bash
repo-scope fastapi/fastapi --html reports/fastapi.html --json reports/fastapi.json
repo-scope facebook/react --stdout
```

## REST API

```text
GET  /api/health
POST /api/analyze
POST /api/compare
POST /api/ai-insight
```

Example request:

```json
{
  "repo": "fastapi/fastapi",
  "refresh": false
}
```

## ML training path

RepoScope does **not** ship a fake pretrained classifier. The training code is ready, but a real classifier should only be trained after collecting and human-labelling repository snapshots.

```bash
pip install -e ".[ml]"
python scripts/export_training_row.py fastapi/fastapi --label healthy
python scripts/export_training_row.py some/repo --label risky
python scripts/train_risk_model.py data/repo_risk_training.csv
```

Training features include recent activity, bus factor, issue closure, PR merge rate, active sample size, CI and test signals. See `docs/ML_TRAINING.md`.

## Deploy

### Vercel

Push this repository to GitHub, import it in Vercel, and set `GITHUB_TOKEN` in Project Settings → Environment Variables. FastAPI is exported as `app` from the root `app.py`, so Vercel can detect it directly. Add `OPENAI_API_KEY` only if you want the LLM analyst.

### Docker

```bash
docker build -t repo-scope .
docker run --rm -p 8000:8000 -e GITHUB_TOKEN=... repo-scope
```

For an AWS path, the same image can be pushed to ECR and run with App Runner or ECS. See `docs/AWS_DEPLOY.md`.

## Important interpretation note

RepoScope intentionally caps paginated GitHub collection to keep interactive analysis fast and respectful of rate limits. Activity, contributor, issue and pull-request metrics are therefore *recent sampled signals*, not a claim to have exhaustively downloaded the repository's entire history.

## Project structure

```text
repo-scope/
├── app.py
├── public/                    # polished web dashboard
├── src/repo_scope/
│   ├── web.py                 # FastAPI application
│   ├── profile.py             # orchestration API
│   ├── fetch/                 # GitHub REST + cache
│   ├── analysis/              # metrics / health / alerts / trends / compare
│   ├── report/                # HTML + JSON reports
│   ├── ml/                    # optional supervised training pipeline
│   └── insights.py            # local + optional LLM analysis
├── scripts/                   # training dataset / model helpers
├── tests/
├── docs/
└── .github/workflows/ci.yml
```
