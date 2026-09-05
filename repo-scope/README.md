# RepoScope

**AI-assisted repository intelligence for GitHub engineering teams.** RepoScope transforms live GitHub signals into an explainable engineering profile: repository health, contributor concentration, maintenance hygiene, Cloud/DevOps readiness, structured AI diagnosis, trends, comparisons and an experimental ML maintenance-risk baseline.

## What ships in v0.6.0

- FastAPI web application and REST API
- Responsive developer-tooling dashboard
- GitHub REST client with authentication, pagination, caching and rate-limit handling
- Explainable 0–100 repository health score
- Bus-factor / contributor concentration analysis
- Issue and pull-request hygiene metrics
- Cloud/DevOps readiness from CI, tests, Docker, IaC, lockfiles and deployment configuration
- Monthly activity time series and repository comparison
- Structured AI diagnosis with deterministic fallback and optional LLM enhancement
- Completed **60,000-repository research catalog**
- **1,267** deep repository snapshots with timestamped engineering evidence
- **697** conservative weak-labelled snapshots for experimental ML
- Durable blind human-review queue and human-label override path
- Blind human-review CLI with reviewer provenance and evidence-note safeguards
- Dataset quality, grouped evaluation, temporal validation, calibration diagnostics and failure-slice analysis
- Random Forest experimental risk baseline with versioned feature schema and reproducible provenance
- Machine-readable model readiness and explicit manual promotion approval
- Standalone HTML/JSON reports and CLI
- Pytest + correctness-focused Ruff CI
- Docker runtime and documented cloud deployment paths

## Architecture

```text
GitHub REST API
      |
      +--> completed 60k research catalog
      |       language / stars / archive state / timestamps / license
      |
      `--> 1,267 deep repository snapshots
              timestamped engineering features
                      |
              independent maintenance evidence
                 /                    \
          weak labels          blind human-review queue
                 \                    /
                  combined training path
                           |
             quality + grouped evaluation
             + temporal holdout + calibration
             + failure-slice diagnostics
                           |
                  experimental model
                           |
                    readiness gate
                           |
                explicit human promotion

Live analysis:
RepoProfile --> health + alerts + cloud readiness + structured AI + optional ML

Serving:
FastAPI --> Dashboard / API / CLI / HTML / JSON
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

`GITHUB_TOKEN` is strongly recommended. `OPENAI_API_KEY` is optional; without it RepoScope keeps the analyst usable through deterministic structured diagnosis.

```env
GITHUB_TOKEN=github_pat_...
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-luna
CACHE_TTL_SECONDS=3600
GITHUB_MAX_PAGES=3
```

Never commit `.env` or production credentials.

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

`/api/analyze` returns deterministic engineering analytics, Cloud/DevOps readiness and the optional `ml_risk` block. `/api/ai-insight` adds structured engineering diagnosis and an optional LLM narrative.

## Experimental ML pipeline

RepoScope deliberately does **not** create ML labels from its own health score. Independent GitHub maintenance evidence drives a conservative weak-label bootstrap:

- explicitly archived repository → `risky`
- latest release ≤150 days and not archived → `healthy`
- latest release ≥180 days and not archived → `watch`
- release age 151–179 days → ambiguous and excluded from weak training
- insufficient independent evidence → skipped rather than guessed

Every accepted training row records label provenance. The eight model features are:

- days since last commit
- bus factor
- issue closure rate
- PR merge rate
- commits in the recent sample
- contributors sampled
- CI presence
- test presence

The final v0.6 research snapshot contains **60,000 catalog repositories**, **1,267 deep snapshots** and **697 weak-labelled snapshots**. Collection was intentionally stopped at the 60k catalog milestone. Historical artifact filenames retain `100k` for pipeline compatibility; those filenames are not claims that 100,000 repositories were collected.

Evaluation is repository-aware: `StratifiedGroupKFold` produces out-of-fold predictions, a grouped holdout checks generalization, and a chronological holdout checks newer repositories without identity leakage. The pipeline also reports per-class metrics, balanced accuracy, calibration diagnostics and failure slices by non-feature context.

The latest trained experimental model is evaluated on all 697 weak-labelled repositories after isolated evaluation and final refit. Grouped cross-validation reports roughly **81.0% macro F1** and **81.3% balanced accuracy**, with expected calibration error around **0.068**. These are weak-supervision research metrics, not independently validated production accuracy.

## Human validation workflow

The next validation step must be performed by real reviewers. RepoScope includes a blind review CLI that reads `data/repo_risk_human_review_queue.csv` but does not expose weak labels, model predictions, confidence, health scores or queue reasons that reveal the weak-label rule.

Run from `repo-scope/`:

```bash
python scripts/review_human_labels.py --reviewer reviewer-a --limit 20
```

The tool shows review-safe repository evidence and the GitHub URL, then stores approved decisions in `data/repo_risk_human_labels.csv`. Reviewer identity and evidence-based notes are mandatory. Existing durable reviews are protected from accidental overwrite.

Human reviewers should follow `docs/HUMAN_LABEL_RUBRIC.md` and inspect public repository evidence independently before assigning `healthy`, `watch` or `risky`.

## Model governance

The deterministic health score remains RepoScope's primary explainable signal. ML is deliberately secondary until independent human validation is sufficient.

The scaled model cannot silently become the default. Promotion requires:

1. minimum class support and dataset-quality gates;
2. grouped and temporal validation thresholds;
3. acceptable calibration and failure-slice diagnostics;
4. a sufficiently large blind human-reviewed validation subset;
5. weak-vs-human agreement checks;
6. an explicit manual promotion decision.

The current automated evidence gates pass, while production promotion remains blocked by the missing independent human-reviewed validation subset. RepoScope does not fabricate human labels to clear that blocker.

See `docs/ML_TRAINING.md`, `docs/HUMAN_LABEL_RUBRIC.md`, `models/repo_risk_100k_model_card.md` and `models/repo_risk_100k_readiness.json` for the detailed methodology and current status.

## Generated ML artifacts

The v0.6 pipeline keeps its historical `100k` artifact names for compatibility:

- `data/repository_catalog_100k.csv` — final 60k broad catalog
- `data/repo_risk_unlabelled_100k.csv` — deep snapshots and evaluation context
- `data/repo_risk_training_100k.csv` — weak-labelled rows
- `data/repo_risk_training_combined_100k.csv` — weak labels plus durable human overrides
- `data/repo_risk_human_review_queue.csv` — blinded review candidates
- `data/repo_risk_human_labels.csv` — durable human-review registry
- `data/repo_risk_100k_quality.json` — dataset quality report
- `data/repo_risk_100k_progress.json` — verified collection counters
- `models/repo_risk_100k_metrics.json` — grouped, temporal, calibration and failure-slice metrics
- `models/repo_risk_100k_model_card.md` — generated Model Card
- `models/repo_risk_100k_readiness.json` — promotion readiness/blockers
- `models/repo_risk_100k_promotion.json` — explicit manual approval record
- `models/repo_risk_100k.joblib` — experimental scaled artifact

## Deploy

Deployment is intentionally a later project phase. The repository already includes Docker and deployment documentation, but v0.6 does not claim a new production deployment.

### Docker / ML-enabled runtime

```bash
docker build -t repo-scope .
docker run --rm -p 8000:8000 -e GITHUB_TOKEN=... repo-scope
```

## Interpretation note

Interactive GitHub analysis intentionally uses bounded API samples to remain fast and respectful of rate limits. Activity, contributor, issue and PR metrics are engineering signals rather than claims about exhaustive repository history. Cloud readiness describes repository delivery posture, not proof of a secure production deployment. The ML model remains experimental weak supervision until independent human validation satisfies the documented promotion policy.

## Project structure

```text
repo-scope/
├── app.py
├── public/                    # engineering dashboard
├── data/                      # catalog, deep snapshots, labels, QA, review queue
├── models/                    # experimental model + evaluation/governance metadata
├── src/repo_scope/
│   ├── web.py                 # FastAPI application
│   ├── profile.py             # orchestration API
│   ├── fetch/                 # GitHub REST + cache
│   ├── analysis/              # health / alerts / trends / cloud readiness
│   ├── report/                # HTML + JSON reports
│   ├── ml/                    # labels / training / optional inference
│   └── insights.py            # structured diagnosis + optional LLM
├── scripts/                   # collection / labeling / QA / training / governance
├── tests/
└── docs/
```
