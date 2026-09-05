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
- Training repositories in latest model: 550

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
- Dataset SHA-256: `c35eb7d8e2a28a293a93c557b068a4cafd6ace069759b5c6cd21f2ab439a14a7`
- Trained at UTC: 2026-09-05T15:37:14.973996+00:00
- scikit-learn: 1.9.0

## Evaluation

- Cross-validation strategy: stratified_group_k_fold
- Cross-validation folds: 5
- Cross-validation accuracy: 0.834545
- Cross-validation balanced accuracy: 0.740414
- Cross-validation macro F1: 0.739095
- Grouped holdout train repositories: 412
- Grouped holdout test repositories: 138
- Holdout accuracy: 0.826087
- Holdout balanced accuracy: 0.772184
- Holdout macro F1: 0.762675

### Temporal holdout

- Available: yes
- Strategy: newest_25pct_repositories_by_snapshot_time
- Cutoff UTC: 2026-09-05T15:35:48.451922+00:00
- Balanced accuracy: 0.530327
- Macro F1: 0.51873
- Missing test classes: []

### Probability calibration diagnostics

- Status: analysis_only_uncalibrated
- Source: repository-grouped out-of-fold probabilities
- Log loss: 0.406114
- Multiclass Brier score: 0.228287
- Expected calibration error (10 bins): 0.042362
- Mean confidence: 0.800833

The probability diagnostics are measured from repository-grouped out-of-fold predictions. They are diagnostic evidence only; RepoScope does not describe the probabilities as calibrated confidence until independent human-reviewed validation supports that claim.

### Cross-validation confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 357 | 0 | 39 |
| watch | 6 | 32 | 11 |
| risky | 22 | 13 | 70 |

### Grouped holdout confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 82 | 0 | 12 |
| watch | 3 | 13 | 3 |
| risky | 3 | 3 | 19 |

### Temporal holdout confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 46 | 0 | 8 |
| watch | 1 | 0 | 2 |
| risky | 4 | 2 | 17 |

### Worst out-of-fold failure slices

**language**
- `JavaScript` — n=10, accuracy=0.4, errors=6
- `Java` — n=19, accuracy=0.631579, errors=7
- `Ruby` — n=12, accuracy=0.666667, errors=4
**repository_size**
- `tiny_lt_1mb` — n=53, accuracy=0.754717, errors=13
- `medium_10mb_100mb` — n=74, accuracy=0.756757, errors=18
- `small_1mb_10mb` — n=61, accuracy=0.836066, errors=10
**maintenance_style**
- `archived` — n=105, accuracy=0.666667, errors=35
- `recent_active` — n=425, accuracy=0.868235, errors=56
- `stale_active` — n=20, accuracy=1.0, errors=0

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
