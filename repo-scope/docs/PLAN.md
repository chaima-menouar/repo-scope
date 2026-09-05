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
- [x] Build a resumable diversity-first catalog/deep-profile collection pipeline
- [x] Complete the requested **60,000-repository catalog milestone** and stop further collection
- [x] Accumulate **1,267 deep repository snapshots** before the 60k stop point
- [x] Build **697 conservative weak-labelled snapshots** for experimental training
- [x] Freeze legacy catalog/deep/dataset workflows as verification-only after the requested 60k stop point
- [x] Preserve the explicit `stopped_at_requested_60k_catalog_milestone` progress marker
- [x] Preserve accumulated deep snapshots when stratified manifests change
- [x] Reject catalog/deep row regressions and duplicate repositories before committing progress
- [x] Define an independent human labelling rubric (`healthy`, `watch`, `risky`)
- [x] Add durable human-label provenance and weak-label override path
- [x] Add a blind human-review CLI that hides weak-label/model signals and requires reviewer provenance + evidence notes
- [x] Add a blind reviewer-assignment planner with deterministic language-balanced ordering and controlled overlap
- [x] Keep assignment files limited to reviewer/repository routing only, with no automated labels or model signals
- [x] Deduplicate queue repositories before reviewer assignment and reject impossible assignment capacity
- [x] Preserve multiple independent reviewer decisions per repository without silent overwrite
- [x] Add strict-majority adjudication that keeps ties/disagreements out of durable ground truth
- [x] Persist a machine-readable adjudication audit with no/partial/full status and unresolved cases
- [x] Reject manually edited decisions missing evidence notes or review timestamps
- [x] Add tests that prevent automation fields from leaking into the reviewer evidence view
- [x] Add tests for reviewer-specific pending queues, controlled assignments and multi-reviewer adjudication
- [x] Add inter-reviewer reliability reporting with raw agreement and Cohen's kappa
- [x] Add tests for reviewer overlap, disagreement and kappa reporting
- [x] Add a dedicated human-validation workflow that performs no repository collection
- [x] Refresh adjudication, weak-vs-human comparison, quality and readiness only from human evidence
- [x] Gate readiness on human-review audit integrity, including duplicate/invalid decision checks
- [x] Require at least 60 repositories with multiple independent reviewers once human comparison is otherwise ready
- [x] Keep Cohen's kappa as an audit metric without inventing an arbitrary promotion threshold
- [x] Document the human-review workflow and raw-vs-adjudicated ground-truth boundary
- [x] Review class balance, missingness and leakage automatically
- [x] Train/evaluate grouped Random Forest baseline
- [x] Benchmark Random Forest against grouped Logistic Regression baseline
- [x] Add grouped cross-validation, balanced accuracy and confusion matrices
- [x] Add chronological holdout on the newest repository snapshots
- [x] Refit the saved inference artifact on all labelled rows after isolated evaluation
- [x] Store dataset hash, model metadata and versioned feature schema
- [x] Fail closed on incompatible model feature schemas
- [x] Gate scaled-model inference on minimum support for all three classes
- [x] Measure out-of-fold probability reliability with log loss, multiclass Brier score and ECE
- [x] Add automated weak-label vs human-review agreement reporting
- [x] Add failure-slice diagnostics for language, repository size and maintenance style
- [x] Add a machine-readable promotion-readiness gate with explicit blocking reasons
- [x] Keep scaled prediction experimental while independent human validation is insufficient
- [ ] Build a sufficiently large stratified human-reviewed validation subset with real independent reviewers
- [ ] Calibrate production-facing probabilities only after independent human validation supports it
- [ ] Promote scaled prediction only after the readiness gate passes and a manual review approves it

### Current v0.6 status

Automated collection and ML evidence are frozen at the requested 60k scope. Reviewer tooling now includes controlled blind assignments, independent decision storage, durable adjudication auditing, reviewer-agreement reporting and readiness integrity checks. Raw reviewer decisions remain separate from adjudicated ground truth. The remaining blockers are intentionally human-governed: real independent reviewers must complete the validation subset at sufficient scale, production-facing probabilities may only be calibrated after that evidence exists, and model promotion still requires an explicit manual decision. RepoScope must not fabricate human labels, invent reviewer identities, restart collection silently, or automatically promote the experimental model.

## v0.7 — durable cloud analytics

Deployment is intentionally deferred until the ML/data phase and portfolio review are accepted.

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
