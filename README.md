# RepoScope

> AI-assisted repository intelligence for GitHub engineering teams.

RepoScope analyzes live GitHub repository signals and converts them into an explainable engineering profile: activity, contributor concentration, issue/PR hygiene, Cloud/DevOps readiness, alerts, trends, comparisons, structured AI recommendations and an experimental ML maintenance-risk baseline.

## Why this project matters

RepoScope is intentionally built as an end-to-end **AI + Cloud + Software Engineering** system rather than a standalone model demo. It combines live data ingestion, explainable analytics, structured AI reasoning, an evidence-traceable ML pipeline, a REST API, CLI/report interfaces, automated testing, containerization and cloud deployment paths.

### Engineering stack

- **Backend:** Python, FastAPI, Pydantic
- **Data source:** GitHub REST API with pagination, authentication, caching and rate-limit handling
- **Analytics:** health scoring, bus factor, issue/PR hygiene, alerts and time series
- **AI:** structured risk diagnosis with evidence + optional LLM enhancement
- **ML:** automated repository-snapshot collection, independent maintenance evidence, weak-label bootstrap, repository-group train/test split and Random Forest baseline
- **Cloud readiness:** CI/CD, tests, Docker, infrastructure-as-code, lockfile and deployment-config detection with a 0–100 posture score
- **Frontend:** responsive engineering intelligence dashboard with Chart.js
- **Cloud / DevOps:** Docker, GitHub Actions, Vercel/Render support and AWS ECR + App Runner/ECS path
- **Interfaces:** Web dashboard, REST API, CLI, JSON and standalone HTML reports

## Architecture

```text
GitHub REST API
      |
      v
Data ingestion + TTL cache
      |
      v
Feature / signal extraction
      |
      +--> Explainable health + alerts
      +--> Cloud / DevOps readiness
      +--> Structured AI diagnosis --> optional LLM enhancement
      `--> Experimental ML baseline
             ^
             | automated evidence-labelled snapshots

FastAPI --> Dashboard / REST API / CLI / HTML / JSON

CI/CD: GitHub Actions --> lint + tests + Docker build
ML automation: collect --> evidence labels --> train --> metrics/model artifact
Cloud delivery: Docker --> Registry --> Render / AWS App Runner or ECS
```

## Key product capabilities

| Capability | What RepoScope demonstrates |
|---|---|
| Repository health | Explainable 0–100 engineering score |
| Contributor risk | Bus-factor and ownership concentration analysis |
| Maintenance hygiene | Issue closure and pull-request merge signals |
| Cloud readiness | Delivery posture derived from CI, tests, containers, IaC, lockfiles and deployment config |
| Structured AI analyst | Top risks, evidence, strengths and prioritized engineering actions |
| Optional LLM | External model enhancement without making the core product dependent on paid AI |
| Trends | Commit velocity and issue-flow time series |
| Comparison | Side-by-side repository benchmarking |
| Experimental ML | Random Forest baseline with label provenance and repository-level leakage controls |
| ML automation | GitHub Actions collection, weak-label bootstrap, model training and metrics generation |
| Cloud delivery | Containerized, environment-configured, CI-tested service |

## ML honesty and provenance

RepoScope does **not** train the model from its own health score. The experimental baseline collects independent maintenance evidence such as GitHub archive status and latest-release age, records `label_source` / `label_evidence`, and skips repositories where there is not enough independent evidence to assign a conservative weak label.

The resulting ML output is explicitly marked **experimental weak supervision**. It is separate from the deterministic health score and is not presented as a calibrated production probability. See [`repo-scope/docs/ML_TRAINING.md`](./repo-scope/docs/ML_TRAINING.md) for the full methodology.

## Project source

The application lives in [`repo-scope/`](./repo-scope). See the full [project README](./repo-scope/README.md), [architecture notes](./repo-scope/docs/ARCHITECTURE.md), [AWS deployment guide](./repo-scope/docs/AWS_DEPLOY.md), and [ML training guide](./repo-scope/docs/ML_TRAINING.md).

## Quick start

```bash
cd repo-scope
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev,ml]"
copy .env.example .env
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` and API documentation at `http://127.0.0.1:8000/docs`.

## Security note

Keep `GITHUB_TOKEN`, `OPENAI_API_KEY` and other credentials in environment variables. Never commit `.env` or production credentials.

---

RepoScope is designed around **explainability over vanity metrics**: sampled GitHub signals and experimental ML outputs are clearly labelled instead of being presented as exhaustive or production-certified truth.
