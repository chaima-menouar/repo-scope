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

## v0.6 — real ML risk model

- [ ] Collect 500+ diverse repository snapshots
- [ ] Define human labelling rubric (`healthy`, `watch`, `risky`)
- [ ] Review class balance and leakage
- [ ] Train/evaluate baseline models
- [ ] Calibrate probabilities
- [ ] Store model metadata and feature version
- [ ] Integrate prediction only after validation

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
