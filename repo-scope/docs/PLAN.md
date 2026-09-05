# RepoScope delivery plan

## v0.5 — deployable product baseline (implemented)

- [x] GitHub REST ingestion
- [x] Token authentication and rate-limit handling
- [x] Pagination and TTL cache
- [x] Descriptive repository metrics
- [x] Health score and bus factor
- [x] Alert engine
- [x] Time-series analysis
- [x] Repository comparison
- [x] Standalone HTML / JSON report
- [x] CLI
- [x] FastAPI API
- [x] Responsive dashboard
- [x] Optional LLM analyst with fallback
- [x] Tests + CI
- [x] Docker / Vercel deployment entrypoint

## v0.6 — experimental ML risk intelligence

- [x] Collect 500+ diverse repository snapshots as the first scale milestone
- [x] Build resumable 100k-catalog / 10k-deep-profile collection pipeline
- [x] Define an independent human labelling rubric (`healthy`, `watch`, `risky`)
- [x] Add durable human-label provenance and weak-label override path
- [x] Review class balance, missingness and leakage automatically
- [x] Train/evaluate grouped Random Forest baseline
- [x] Add grouped cross-validation, balanced accuracy and confusion matrices
- [x] Add chronological holdout on the newest repository snapshots
- [x] Refit the saved inference artifact on all labelled rows after isolated evaluation
- [x] Store dataset hash, model metadata and versioned feature schema
- [x] Fail closed on incompatible model feature schemas
- [x] Gate scaled-model inference on minimum support for all three classes
- [ ] Build a sufficiently large stratified human-reviewed validation subset
- [ ] Measure/calibrate probabilities before treating them as confidence
- [ ] Compare weak-label and human-label performance separately
- [ ] Promote scaled prediction only after the validation checklist passes

## v0.7 — durable cloud analytics

- [ ] AWS ECR + App Runner/ECS deployment
- [ ] DynamoDB/Postgres snapshots
- [ ] Scheduled repository re-analysis
- [ ] Drift alerts between snapshots
- [ ] Authentication / saved repository workspaces

## v0.8 — product intelligence

- [ ] GitHub App installation flow
- [ ] Organization-level portfolio dashboard
- [ ] PR/issue semantic categorization
- [ ] Team-level risk trends
