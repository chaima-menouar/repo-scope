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
- **ML:** scalable repository catalog collection, deep repository snapshots, independent maintenance evidence, weak-label bootstrap, repository-grouped evaluation and Random Forest baseline
- **Data quality:** class balance, label provenance, feature missingness, catalog diversity and explicit quality warnings
- **Cloud readiness:** CI/CD, tests, Docker, infrastructure-as-code, lockfile and deployment-config detection with a 0–100 posture score
- **Frontend:** responsive engineering intelligence dashboard with Chart.js
- **Cloud / DevOps:** Docker, GitHub Actions, Vercel/Render support and AWS ECR + App Runner/ECS path
- **Interfaces:** Web dashboard, REST API, CLI, JSON and standalone HTML reports

## Architecture

```text
GitHub REST API
      |
      +--> 100k repository catalog target
      |       metadata: language, activity timestamps, archive state,
      |       stars, forks, size, license and repository identity
      |
      `--> 10k deep-profile target
              commits + contributors + issues + PRs + engineering signals
                      |
                      v
              independent maintenance evidence
                      |
                      v
              conservative weak labels
                      |
                      +--> dataset quality report
                      |
                      `--> grouped ML evaluation + model artifact

Live analysis path:
GitHub --> feature extraction --> health + alerts + cloud posture + AI diagnosis

Serving path:
FastAPI --> Dashboard / REST API / CLI / HTML / JSON

CI/CD: GitHub Actions --> lint + tests + Docker build
ML automation: catalog --> deep snapshots --> evidence labels --> quality gate --> train --> metrics/model
Cloud delivery: Docker --> Registry --> Render / AWS App Runner or ECS
```

## Data and training strategy

RepoScope deliberately separates **catalog scale** from **deep-analysis scale**.

- **100,000 repository catalog target:** broad GitHub coverage used to build a diverse candidate pool across languages, ages, activity levels, popularity bands and archive states.
- **10,000 deep repository target:** a stratified subset receives the more expensive RepoScope analysis required for model features.
- **Incremental collection:** GitHub Actions adds bounded batches and resumes from committed progress instead of attempting an unsafe one-shot crawl.
- **Independent labels:** weak labels are derived from external maintenance evidence such as archive state and release recency, never from RepoScope's own health score.
- **Quality reporting:** every refresh can generate class balance, label-source distribution, missingness, language/license mix and warnings about weak coverage.
- **Leakage controls:** repositories are grouped during evaluation so snapshots from one repository cannot appear on both sides of an evaluation split.
- **Cross-validation:** the training pipeline uses stratified grouped folds when class support allows it, in addition to a repository-grouped holdout.

The current committed dataset/model status should always be read from generated progress and metrics artifacts; target numbers are not presented as already collected until those artifacts verify completion.

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
| ML evaluation | Stratified grouped cross-validation, grouped holdout and explicit optimism warnings |
| Dataset QA | Missingness, class balance, provenance and catalog-diversity reporting |
| ML automation | GitHub Actions collection, weak-label bootstrap, quality reporting, model training and metrics generation |
| Cloud delivery | Containerized, environment-configured, CI-tested service |

## ML honesty and provenance

RepoScope does **not** train the model from its own health score. The experimental baseline collects independent maintenance evidence such as GitHub archive status and latest-release age, records `label_source` / `label_evidence`, and skips repositories where there is not enough independent evidence to assign a conservative weak label.

The resulting ML output is explicitly marked **experimental weak supervision**. It is separate from the deterministic health score and is not presented as a calibrated production probability. A high validation score on weak labels is treated as a signal to investigate possible task simplicity or label-source artifacts, not as proof of real-world production accuracy.

See [`repo-scope/docs/ML_TRAINING.md`](./repo-scope/docs/ML_TRAINING.md) for the full methodology.

## Generated ML artifacts

As the automated pipeline advances, these files describe the actual state rather than the target state:

- `repo-scope/data/repository_catalog_100k.csv` — accumulated catalog
- `repo-scope/data/repo_risk_unlabelled_100k.csv` — deep analyzed snapshots
- `repo-scope/data/repo_risk_training_100k.csv` — evidence-labelled training rows
- `repo-scope/data/repo_risk_100k_quality.json` — dataset quality report
- `repo-scope/data/repo_risk_100k_progress.json` — collection counters and status
- `repo-scope/models/repo_risk_100k_metrics.json` — evaluation output when enough labelled data exists
- `repo-scope/models/repo_risk_100k.joblib` — experimental model artifact

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
