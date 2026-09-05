# RepoScope Risk Model Card

> Status: **experimental weak supervision**. This model is a secondary research signal, not a calibrated production risk score.

## Intended use

RepoScope uses this model to explore whether repository-maintenance risk can be learned from engineering signals that are separate from the deterministic health score. The deterministic score remains the primary explainable signal.

## Data snapshot

- Catalog target: 100000
- Catalog repositories collected: 40000
- Deep-profile target: 10000
- Deep snapshots collected: 797
- Labelled snapshots: 388
- Human-review queue: 250
- Training repositories in latest model: 338

### Label distribution

- `healthy`: 298
- `risky`: 55
- `watch`: 35

### Label provenance

- `recent_release_evidence`: 298
- `github_archived_flag`: 55
- `stale_release_evidence`: 35

Weak labels are based on independent GitHub maintenance evidence. RepoScope's deterministic health score is never used as the training target.

## Model and reproducibility

- Model: RandomForestClassifier
- Feature schema: `reposcope-risk-features-v1`
- Artifact fit strategy: refit_on_all_rows_after_isolated_evaluation
- Source CSV: `data/repo_risk_training_100k.csv`
- Dataset SHA-256: `41a116afe5b4694731e4a223d6a096f44f5b284fd8b2b835d45f74c2a4d42ef2`
- Trained at UTC: 2026-09-05T14:40:43.480121+00:00
- scikit-learn: 1.9.0

## Evaluation

- Cross-validation strategy: stratified_group_k_fold
- Cross-validation folds: 4
- Cross-validation accuracy: 0.872781
- Cross-validation balanced accuracy: 0.524104
- Cross-validation macro F1: 0.508858
- Grouped holdout train repositories: 253
- Grouped holdout test repositories: 85
- Holdout accuracy: 0.929412
- Holdout balanced accuracy: 0.916667
- Holdout macro F1: 0.580504

### Temporal holdout

- Available: yes
- Strategy: newest_25pct_repositories_by_snapshot_time
- Cutoff UTC: 2026-09-05T13:53:07.468860+00:00
- Balanced accuracy: 0.770833
- Macro F1: 0.518122
- Missing test classes: ['watch']

### Probability calibration diagnostics

- Status: n/a
- Source: n/a
- Log loss: n/a
- Multiclass Brier score: n/a
- Expected calibration error (10 bins): n/a
- Mean confidence: n/a

The probability diagnostics are measured from repository-grouped out-of-fold predictions. They are diagnostic evidence only; RepoScope does not describe the probabilities as calibrated confidence until independent human-reviewed validation supports that claim.

### Cross-validation confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 265 | 0 | 23 |
| watch | 3 | 0 | 1 |
| risky | 16 | 0 | 30 |

### Grouped holdout confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 70 | 1 | 4 |
| watch | 0 | 0 | 0 |
| risky | 1 | 0 | 9 |

### Temporal holdout confusion matrix

| actual \ predicted | healthy | watch | risky |
| --- | ---: | ---: | ---: |
| healthy | 6 | 0 | 3 |
| watch | 0 | 0 | 0 |
| risky | 2 | 0 | 14 |

### Worst out-of-fold failure slices

Not available yet. Newer deep snapshots retain non-feature context for this analysis.

Slice context such as language and repository size is retained only for evaluation and is not part of the risk model feature vector.

### Automated evaluation warning

Small weakly-labelled dataset; metrics may be optimistic and must not be treated as production performance. Signals: at least one class has fewer than 20 repositories; balanced accuracy is below 0.60, indicating weak minority-class performance.

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
