# RepoScope Risk Model Card

> Status: **experimental weak supervision**. This model is a secondary research signal, not a calibrated production risk score.

## Intended use

RepoScope uses this model to explore whether repository-maintenance risk can be learned from engineering signals that are separate from the deterministic health score. The deterministic score remains the primary explainable signal.

## Data snapshot

- Catalog target: 100000
- Catalog repositories collected: 40000
- Deep-profile target: 10000
- Deep snapshots collected: 913
- Labelled snapshots: 464
- Human-review queue: 250
- Training repositories in latest model: 464

### Label distribution

- `healthy`: 339
- `risky`: 80
- `watch`: 45

### Label provenance

- `recent_release_evidence`: 339
- `github_archived_flag`: 80
- `stale_release_evidence`: 45

Weak labels are based on independent GitHub maintenance evidence. RepoScope's deterministic health score is never used as the training target.

## Model and reproducibility

- Model: RandomForestClassifier
- Feature schema: `reposcope-risk-features-v1`
- Artifact fit strategy: refit_on_all_rows_after_isolated_evaluation
- Source CSV: `data/repo_risk_training_combined_100k.csv`
- Dataset SHA-256: `ac9767c61f2a84f158c99ae2872aa7609b78e95ec8c843e41a67b337f20b2a20`
- Trained at UTC: 2026-09-05T15:34:13.597808+00:00
- scikit-learn: 1.9.0

## Evaluation

- Cross-validation strategy: stratified_group_k_fold
- Cross-validation folds: 5
- Cross-validation accuracy: 0.838362
- Cross-validation balanced accuracy: 0.750422
- Cross-validation macro F1: 0.74392
- Grouped holdout train repositories: 348
- Grouped holdout test repositories: 116
- Holdout accuracy: 0.862069
- Holdout balanced accuracy: 0.820924
- Holdout macro F1: 0.810811

### Temporal holdout

- Available: yes
- Strategy: newest_25pct_repositories_by_snapshot_time
- Cutoff UTC: 2026-09-05T15:33:15.237116+00:00
- Balanced accuracy: 0.785185
- Macro F1: 0.783387
- Missing test classes: []

### Probability calibration diagnostics

- Status: analysis_only_uncalibrated
- Source: repository-grouped out-of-fold probabilities
- Log loss: 0.415699
- Multiclass Brier score: 0.231644
- Expected calibration error (10 bins): 0.036407
- Mean confidence: 0.80714

The probability diagnostics are measured from repository-grouped out-of-fold predictions. They are diagnostic evidence only; RepoScope does not describe the probabilities as calibrated confidence until independent human-reviewed validation supports that claim.

### Cross-validation confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 306 | 1 | 32 |
| watch | 5 | 32 | 8 |
| risky | 18 | 11 | 51 |

### Grouped holdout confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 69 | 0 | 8 |
| watch | 0 | 11 | 4 |
| risky | 2 | 2 | 20 |

### Temporal holdout confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 25 | 0 | 5 |
| watch | 1 | 8 | 1 |
| risky | 3 | 2 | 13 |

### Worst out-of-fold failure slices

**language**
- `JavaScript` — n=6, accuracy=0.5, errors=3
- `Go` — n=8, accuracy=0.625, errors=3
- `C++` — n=9, accuracy=0.666667, errors=3
**repository_size**
- `medium_10mb_100mb` — n=45, accuracy=0.711111, errors=13
- `tiny_lt_1mb` — n=35, accuracy=0.8, errors=7
- `small_1mb_10mb` — n=35, accuracy=0.828571, errors=6
**maintenance_style**
- `archived` — n=80, accuracy=0.6375, errors=29
- `recent_active` — n=365, accuracy=0.876712, errors=45
- `stale_active` — n=19, accuracy=0.947368, errors=1

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
