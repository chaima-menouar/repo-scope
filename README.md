# RepoScope

> AI-assisted repository intelligence for GitHub engineering teams.

RepoScope analyzes live GitHub repository signals and converts them into an explainable engineering profile: activity, contributor concentration, issue/PR hygiene, Cloud/DevOps readiness, alerts, trends, comparisons, structured AI recommendations and an experimental ML maintenance-risk baseline.

## Why this project matters

RepoScope is intentionally built as an end-to-end **AI + Cloud + Software Engineering** system rather than a standalone model demo. It combines live data ingestion, explainable analytics, structured AI reasoning, an evidence-traceable ML pipeline, a REST API, CLI/report interfaces, automated testing, containerization and cloud deployment paths.

## Current verified ML scope

The collection phase is complete for the requested project scope:

- **60,000 repositories** in the broad research catalog
- **1,267 deep repository snapshots**
- **697 conservative weak-labelled snapshots**
- **250 ambiguous cases** exported for blinded human review
- **0 fabricated human labels**
- collection intentionally stopped at the 60k milestone

The trained risk model remains **experimental weak supervision**. Its automated evaluation includes repository-grouped cross-validation, grouped holdout, temporal holdout, probability-reliability diagnostics and failure-slice analysis. Production promotion is intentionally blocked until a sufficiently large independent human-reviewed validation subset exists.

Internal artifact filenames still contain `100k` because they are stable names inherited from the earlier scale design. They are kept for compatibility and do not imply that 100,000 repositories were collected.

## Engineering stack

- **Backend:** Python, FastAPI, Pydantic
- **Data source:** GitHub REST API with pagination, authentication, caching and rate-limit handling
- **Analytics:** health scoring, bus factor, issue/PR hygiene, alerts and time series
- **AI:** structured risk diagnosis with evidence + optional LLM enhancement
- **ML:** weakly supervised repository-risk baseline with grouped and temporal validation
- **Data quality:** class balance, label provenance, missingness, diversity checks and failure slices
- **Frontend:** responsive engineering intelligence dashboard with Chart.js
- **Cloud / DevOps:** Docker, GitHub Actions, environment-based secrets and an AWS deployment path
- **Interfaces:** Web dashboard, REST API, CLI, JSON and standalone HTML reports

## Architecture

```text
GitHub REST API
      |
      +--> 60k repository research catalog (completed)
      |       language + age + popularity + archive state + metadata
      |
      `--> 1,267 deep snapshots (completed scope)
              language × popularity × maintenance-state diversity
                      |
              timestamped engineering features
                      |
              independent maintenance evidence
                      |
              +-------+----------------------+
              |                              |
              v                              v
      conservative weak labels        ambiguous review queue
              |                              |
              |                       durable human labels
              |                              |
              +-------------+----------------+
                            v
                    combined training set
                            |
             grouped CV + grouped holdout
             + temporal holdout + calibration
             + failure-slice diagnostics
                            |
                            v
                 experimental model artifact
                            |
                  readiness policy report
                            |
               explicit human promotion only

Live analysis path:
GitHub --> feature extraction --> health + alerts + cloud posture + AI diagnosis

Serving path:
FastAPI --> Dashboard / REST API / CLI / HTML / JSON

CI/CD: GitHub Actions --> lint + tests + Docker build
Cloud delivery: intentionally deferred to a later phase
```

## ML methodology

RepoScope does **not** train the model from its own health score.

Weak labels are derived from independent maintenance evidence:

- archived repository → `risky`
- non-archived repository with a recent release → `healthy`
- non-archived repository with an older release → `watch`
- ambiguous or insufficient evidence → excluded from weak training

The model uses eight engineering features:

- `days_since_last_commit`
- `bus_factor`
- `issue_closure_rate_pct`
- `pr_merge_rate_pct`
- `commits_90d`
- `contributors_sampled`
- `has_ci`
- `has_tests`

Repository identity is always the evaluation split unit, preventing the same repository from leaking across train/test partitions.

Evaluation includes:

- stratified grouped cross-validation
- grouped holdout
- chronological holdout
- per-class precision, recall and F1
- macro F1 and balanced accuracy
- confusion matrices
- log loss, multiclass Brier score and ECE
- failure slices by language, repository size and maintenance style

Probability outputs remain diagnostic rather than production-calibrated confidence scores until independent human validation supports calibration.

## Promotion safety

The scaled model cannot silently become the default production risk signal.

Promotion requires all of the following:

1. automated readiness checks pass;
2. human-vs-weak validation is sufficiently large and diverse;
3. probability calibration is justified by independent validation;
4. an explicit manual approval record is set.

Until then, the deterministic health score remains the primary explainable signal and ML remains secondary experimental evidence.

## Key product capabilities

| Capability | What RepoScope demonstrates |
|---|---|
| Repository health | Explainable 0–100 engineering score |
| Contributor risk | Bus-factor and ownership concentration analysis |
| Maintenance hygiene | Issue closure and pull-request merge signals |
| Cloud readiness | CI, tests, containers, IaC, lockfiles and deployment-config posture |
| Structured AI analyst | Top risks, evidence, strengths and prioritized actions |
| Optional LLM | Richer interpretation without making the core product depend on paid AI |
| Trends | Commit velocity and issue-flow time series |
| Comparison | Side-by-side repository benchmarking |
| Experimental ML | Random Forest risk baseline with independent weak-label provenance |
| ML evaluation | Grouped CV, grouped holdout, temporal holdout, calibration diagnostics and failure slices |
| Dataset QA | Missingness, class balance, provenance and catalog-diversity reporting |
| Human review | Blinded rubric, durable labels and weak-vs-human comparison path |
| Promotion safety | Readiness report + feature schema + explicit manual promotion record |
| Cloud delivery | Containerized, environment-configured, CI-tested service |

## Generated ML artifacts

These generated files are the source of truth for current state:

- `repo-scope/data/repository_catalog_100k.csv`
- `repo-scope/data/seed_repositories_100k.txt`
- `repo-scope/data/repo_risk_unlabelled_100k.csv`
- `repo-scope/data/repo_risk_training_100k.csv`
- `repo-scope/data/repo_risk_training_combined_100k.csv`
- `repo-scope/data/repo_risk_human_review_queue.csv`
- `repo-scope/data/repo_risk_human_labels.csv`
- `repo-scope/data/repo_risk_human_weak_comparison.json`
- `repo-scope/data/repo_risk_100k_quality.json`
- `repo-scope/data/repo_risk_100k_progress.json`
- `repo-scope/models/repo_risk_100k_metrics.json`
- `repo-scope/models/repo_risk_100k_model_card.md`
- `repo-scope/models/repo_risk_100k_readiness.json`
- `repo-scope/models/repo_risk_100k_promotion.json`
- `repo-scope/models/repo_risk_100k.joblib`

## Project source

The application lives in [`repo-scope/`](./repo-scope).

Useful documentation:

- [Architecture](./repo-scope/docs/ARCHITECTURE.md)
- [ML training methodology](./repo-scope/docs/ML_TRAINING.md)
- [Human-label rubric](./repo-scope/docs/HUMAN_LABEL_RUBRIC.md)
- [AWS deployment path](./repo-scope/docs/AWS_DEPLOY.md)
- [Delivery plan](./repo-scope/docs/PLAN.md)

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
