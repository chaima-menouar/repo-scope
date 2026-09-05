# RepoScope Risk Model Card

> Status: **experimental weak supervision**. This model is a secondary research signal, not a calibrated production risk score.

## Intended use

RepoScope uses this model to explore whether repository-maintenance risk can be learned from engineering signals that are separate from the deterministic health score. The deterministic score remains the primary explainable signal.

## Data snapshot

- Catalog target: 60000
- Catalog repositories collected: 60000
- Deep-profile target: 10000
- Deep snapshots collected: 1267
- Labelled snapshots: 697
- Human-review queue: 250
- Training repositories in latest model: 697

### Label distribution

- `healthy`: 466
- `risky`: 138
- `watch`: 93

### Label provenance

- `recent_release_evidence`: 466
- `github_archived_flag`: 138
- `stale_release_evidence`: 93

Weak labels are based on independent GitHub maintenance evidence. RepoScope's deterministic health score is never used as the training target.

## Model and reproducibility

- Model: RandomForestClassifier
- Feature schema: `reposcope-risk-features-v1`
- Artifact fit strategy: refit_on_all_rows_after_isolated_evaluation
- Source CSV: `data/repo_risk_training_combined_100k.csv`
- Dataset SHA-256: `2b9843f0daad5e5acb4298d4408284863896a1838e3186392f10840170b0fcb3`
- Trained at UTC: 2026-09-05T17:15:41.102784+00:00
- scikit-learn: 1.9.0

## Evaluation

- Cross-validation strategy: stratified_group_k_fold
- Cross-validation folds: 5
- Cross-validation accuracy: 0.843615
- Cross-validation balanced accuracy: 0.813011
- Cross-validation macro F1: 0.810408
- Grouped holdout train repositories: 522
- Grouped holdout test repositories: 175
- Holdout accuracy: 0.8
- Holdout balanced accuracy: 0.739153
- Holdout macro F1: 0.720531

### Temporal holdout

- Available: yes
- Strategy: newest_25pct_repositories_by_snapshot_time
- Cutoff UTC: 2026-09-05T15:41:47.123303+00:00
- Balanced accuracy: 0.87242
- Macro F1: 0.847619
- Missing test classes: []

### Probability calibration diagnostics

- Status: analysis_only_uncalibrated
- Source: repository-grouped out-of-fold probabilities
- Log loss: 0.405456
- Multiclass Brier score: 0.222535
- Expected calibration error (10 bins): 0.06828
- Mean confidence: 0.797354

The probability diagnostics are measured from repository-grouped out-of-fold predictions. They are diagnostic evidence only; RepoScope does not describe the probabilities as calibrated confidence until independent human-reviewed validation supports that claim.

### Cross-validation confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 406 | 0 | 60 |
| watch | 11 | 71 | 11 |
| risky | 22 | 5 | 111 |

### Grouped holdout confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 106 | 0 | 19 |
| watch | 3 | 15 | 3 |
| risky | 5 | 5 | 19 |

### Temporal holdout confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 42 | 0 | 9 |
| watch | 5 | 36 | 2 |
| risky | 0 | 1 | 22 |

### Worst out-of-fold failure slices

**language**
- `Shell` — n=22, accuracy=0.590909, errors=9
- `JavaScript` — n=11, accuracy=0.636364, errors=4
- `Java` — n=27, accuracy=0.703704, errors=8
**repository_size**
- `small_1mb_10mb` — n=106, accuracy=0.801887, errors=21
- `medium_10mb_100mb` — n=115, accuracy=0.817391, errors=21
- `large_ge_100mb` — n=53, accuracy=0.830189, errors=9
**maintenance_style**
- `archived` — n=138, accuracy=0.804348, errors=27
- `recent_active` — n=505, accuracy=0.837624, errors=82
- `stale_active` — n=54, accuracy=1.0, errors=0

Slice context such as language and repository size is retained only for evaluation and is not part of the risk model feature vector.

### Automated evaluation warning

No automated evaluation warning was emitted.

### Dataset-quality warnings

- None reported by the automated dataset-quality checks.

## Known limitations

- Current automated training targets are dominated by weak labels until the durable human-review registry grows.
- Archive/release evidence may encode a simpler maintenance concept than real engineering risk.
- Probability diagnostics do not equal production calibration.
- GitHub API features are sampled and rate-limited rather than exhaustive history.
- Performance must be confirmed on an independently reviewed human-labelled subset before any production promotion.

## Promotion requirements

The model stays experimental until the project has meaningful class support, human-reviewed labels, stable repository-grouped cross-validation, a valid temporal holdout, acceptable calibration diagnostics and documented failure-case review. The generated readiness report remains the machine-readable gate; passing it still requires a manual promotion decision.

This file is generated from RepoScope's committed progress, quality and metrics artifacts so it should not claim collection or performance numbers that those artifacts do not contain.
