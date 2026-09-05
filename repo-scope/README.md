# RepoScope

**AI-assisted repository intelligence for GitHub engineering teams.** RepoScope transforms live GitHub signals into an explainable engineering profile: repository health, contributor concentration, maintenance hygiene, Cloud/DevOps readiness, structured AI diagnosis, trends, comparisons and an experimental ML maintenance-risk baseline.

## What ships in v0.6.0

- FastAPI web application and REST API
- Responsive developer-tooling dashboard
- GitHub REST API client with authentication, pagination, caching and rate-limit handling
- Explainable 0–100 repository health score
- Bus-factor / contributor concentration analysis
- Issue and pull-request hygiene metrics
- CI, tests, README, license, contributing and security-policy detection
- Cloud/DevOps readiness score based on CI, tests, Docker, IaC, lockfiles and deployment config
- Monthly commit and issue time series
- Repository comparison
- Structured AI diagnosis with top risks, evidence, strengths and next actions
- Optional OpenAI narrative enhancement with deterministic fallback
- Automated repository-snapshot dataset collection in GitHub Actions
- Conservative weak labels based on independent maintenance evidence
- Random Forest experimental risk baseline with repository-group train/test split
- Label provenance, feature importance and evaluation metrics
- Optional ML inference that fails closed when the artifact/dependencies are unavailable
- Standalone HTML and JSON reports
- CLI package (`repo-scope owner/repo`)
- Pytest + correctness-focused Ruff CI
- Docker runtime with ML support, plus Vercel/Render and AWS deployment paths

## Architecture

```text
GitHub REST API
      |
      v
RepoProfile / feature extraction
      |
      +--> Explainable health + alerts
      +--> Cloud / DevOps readiness
      +--> Structured AI diagnosis --> optional LLM
      `--> Experimental ML inference

FastAPI --> Dashboard / API / CLI / HTML / JSON

Offline ML:
seed repos --> snapshots --> independent evidence --> weak labels
           --> repository-group split --> Random Forest --> model + metrics
```

## Local run

Requires Python 3.12+.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev,ml]"
copy .env.example .env
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` and API docs at `http://127.0.0.1:8000/docs`.

### Environment variables

`GITHUB_TOKEN` is strongly recommended. `OPENAI_API_KEY` is optional; without it RepoScope keeps the AI analyst usable through the local structured diagnosis.

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

`/api/analyze` includes deterministic health analytics, Cloud/DevOps readiness and the optional `ml_risk` block. `/api/ai-insight` adds the structured engineering diagnosis and optional LLM narrative.

## Experimental ML pipeline

RepoScope does **not** create ML labels from its own health score. GitHub Actions collects repository snapshots and independent maintenance evidence, then applies a conservative weak-label policy:

- GitHub explicitly archived → `risky`
- latest release ≤ 180 days and not archived → `healthy`
- older release and not archived → `watch`
- insufficient independent evidence → skipped rather than guessed

Each training row records `label_source` and `label_evidence`. The model uses only these eight features:

- days since last commit
- bus factor
- issue closure rate
- PR merge rate
- commits in the recent sample
- contributors sampled
- CI presence
- test presence

Training uses a repository-group split to prevent the same repository appearing in both train and test. The resulting class probabilities are explicitly marked **experimental weak supervision**, not calibrated production risk.

```bash
python scripts/collect_training_data.py
python scripts/bootstrap_weak_labels.py
python scripts/train_risk_model.py data/repo_risk_training.csv --output models/repo_risk.joblib
```

See `docs/ML_TRAINING.md` for the methodology and limitations.

## Deploy

### Vercel / lightweight runtime

The deterministic analytics and AI fallback work without the optional ML dependencies. Configure `GITHUB_TOKEN` in environment variables, and add `OPENAI_API_KEY` only when the external LLM narrative is desired.

### Docker / ML-enabled runtime

```bash
docker build -t repo-scope .
docker run --rm -p 8000:8000 -e GITHUB_TOKEN=... repo-scope
```

The Docker image installs the ML optional dependencies and includes the generated model artifact. The same image can be pushed to AWS ECR and deployed through App Runner or ECS. See `docs/AWS_DEPLOY.md`.

## Interpretation note

RepoScope intentionally caps paginated GitHub collection to keep interactive analysis fast and respectful of API limits. Activity, contributor, issue and PR metrics are recent sampled signals rather than claims about an exhaustive repository history. Cloud readiness describes repository delivery signals, not proof of a secure live deployment. The ML model remains experimental until a larger independently reviewed human-labelled dataset replaces weak supervision.

## Project structure

```text
repo-scope/
├── app.py
├── public/                    # responsive engineering dashboard
├── data/                      # seed list + generated ML snapshots
├── models/                    # experimental model + evaluation metadata
├── src/repo_scope/
│   ├── web.py                 # FastAPI application
│   ├── profile.py             # orchestration API
│   ├── fetch/                 # GitHub REST + cache
│   ├── analysis/              # health / alerts / trends / cloud readiness
│   ├── report/                # HTML + JSON reports
│   ├── ml/                    # labels / training / optional inference
│   └── insights.py            # structured diagnosis + optional LLM
├── scripts/                   # collection / labeling / training helpers
├── tests/
└── docs/
```
