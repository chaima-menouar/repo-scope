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
- **ML:** scalable repository catalog collection, stratified deep snapshots, independent maintenance evidence, weak-label bootstrap, durable human review, repository-grouped evaluation and Random Forest baseline
- **Data quality:** class balance, label provenance, feature missingness, catalog diversity, failure slices and explicit quality warnings
- **Cloud readiness:** CI/CD, tests, Docker, infrastructure-as-code, lockfile and deployment-config detection with a 0–100 posture score
- **Frontend:** responsive engineering intelligence dashboard with Chart.js
- **Cloud / DevOps:** Docker, GitHub Actions, Vercel/Render support and AWS ECR + App Runner/ECS path
- **Interfaces:** Web dashboard, REST API, CLI, JSON and standalone HTML reports

## Architecture

```text
GitHub REST API
      |
      +--> 100k repository catalog target
      |       language + age + popularity + archive state + metadata
      |
      `--> 10k stratified deep-profile target
              language × popularity × maintenance-state diversity
                      |
              timestamped snapshots + engineering features
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
             quality + grouped CV + holdout
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
Cloud delivery: Docker --> Registry --> Render / AWS App Runner or ECS
```

## Data and training strategy

RepoScope deliberately separates **catalog scale** from **deep-analysis scale**.

- **100,000 repository catalog target:** broad GitHub coverage across languages, ages, activity levels, popularity bands and archive states.
- **10,000 deep repository target:** a stratified subset receives expensive feature extraction. Sampling mixes language, popularity, active/archived state and a stale-active sampling proxy without using that proxy as the target.
- **Timestamped snapshots:** deep rows record `snapshot_at_utc` for temporal evaluation and future drift analysis.
- **Incremental collection:** bounded, resumable GitHub Actions batches checkpoint progress instead of attempting a one-shot crawl.
- **Branch-safe continuation:** while the work remains on `improve/portfolio-ai-cloud`, a guarded trigger advances one new batch only after the previous run completes; no merge or deployment is required for collection to continue.
- **Independent labels:** weak labels are derived from archive/release evidence, never from RepoScope's own health score.
- **Human-review path:** ambiguous cases go to a blinded review queue and durable human-label registry with reviewer provenance.
- **Weak-vs-human comparison:** agreement and confusion are measured once enough independent human reviews exist.
- **Quality reporting:** each refresh measures balance, provenance, missingness and catalog diversity.
- **Leakage controls:** repository identity is the split unit.
- **Evaluation:** stratified grouped cross-validation, grouped holdout, chronological holdout, balanced metrics and confusion matrices.
- **Probability reliability:** out-of-fold log loss, multiclass Brier score and 10-bin expected calibration error are measured, but probabilities remain explicitly uncalibrated for production use.
- **Failure slices:** out-of-fold errors are sliced by non-feature context such as language, repository size and maintenance style.
- **Reproducibility:** artifacts record source CSV, dataset SHA-256, feature-schema version, fit strategy, training timestamp, model type and scikit-learn version.
- **Promotion safety:** a scaled artifact must pass automated readiness gates and then receive separate explicit human promotion approval before it can become the default inference model.

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
| Experimental ML | Random Forest baseline with independent label provenance and repository-level leakage controls |
| ML evaluation | Grouped CV, grouped holdout, temporal holdout, balanced metrics, calibration diagnostics and failure slices |
| Dataset QA | Missingness, class balance, provenance and catalog-diversity reporting |
| Human review | Blinded rubric, durable labels, weak-label overrides and weak-vs-human agreement reporting |
| Promotion safety | Readiness report + versioned feature schema + explicit manual promotion record |
| ML automation | GitHub Actions collection, labeling, review queue, QA, training, Model Card and readiness generation |
| Cloud delivery | Containerized, environment-configured, CI-tested service |

## ML honesty and provenance

RepoScope does **not** train the model from its own health score. The experimental baseline collects independent maintenance evidence, records `label_source` / `label_evidence`, and skips repositories where there is not enough evidence for a conservative weak label.

The ML output is explicitly marked **experimental weak supervision**. A high weak-label score is treated as a reason to inspect task simplicity or label artifacts, not as proof of real-world accuracy. Probability values are diagnostic until independent human validation supports calibration, and the scaled model cannot silently replace the fallback artifact.

See [`repo-scope/docs/ML_TRAINING.md`](./repo-scope/docs/ML_TRAINING.md) and [`repo-scope/docs/HUMAN_LABEL_RUBRIC.md`](./repo-scope/docs/HUMAN_LABEL_RUBRIC.md) for the full methodology.

## Generated ML artifacts

As the pipeline advances, these files describe the actual state rather than the target state:

- `repo-scope/data/repository_catalog_100k.csv` — accumulated broad repository catalog
- `repo-scope/data/seed_repositories_100k.txt` — stratified deep-analysis manifest
- `repo-scope/data/repo_risk_unlabelled_100k.csv` — timestamped deep snapshots plus non-feature evaluation context
- `repo-scope/data/repo_risk_training_100k.csv` — evidence-labelled weak training rows
- `repo-scope/data/repo_risk_training_combined_100k.csv` — weak labels merged with durable human overrides
- `repo-scope/data/repo_risk_human_review_queue.csv` — ambiguous rows prepared for blinded human review
- `repo-scope/data/repo_risk_human_labels.csv` — durable human-review registry
- `repo-scope/data/repo_risk_human_weak_comparison.json` — weak-vs-human agreement report
- `repo-scope/data/repo_risk_100k_quality.json` — dataset quality report
- `repo-scope/data/repo_risk_100k_progress.json` — collection counters and status
- `repo-scope/models/repo_risk_100k_metrics.json` — grouped, temporal, calibration and failure-slice evaluation output
- `repo-scope/models/repo_risk_100k_model_card.md` — generated truthful Model Card
- `repo-scope/models/repo_risk_100k_readiness.json` — machine-readable promotion blockers/readiness
- `repo-scope/models/repo_risk_100k_promotion.json` — explicit manual promotion approval record; default is `approved: false`
- `repo-scope/models/repo_risk_100k.joblib` — scaled experimental model artifact when training gates are met

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
