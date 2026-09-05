# ML training strategy

RepoScope separates three forms of intelligence on purpose:

1. **Health score** — deterministic, explainable rules that work immediately.
2. **AI diagnosis** — structured evidence and recommendations, with an optional LLM enhancement.
3. **Experimental ML risk baseline** — a supervised Random Forest trained from collected repository snapshots.

The ML model is not presented as production ground truth. Its current labels are conservative **weak labels** built from maintenance evidence that is independent from the eight model features, with a separate durable path for independent human review.

## Completed collection scope

The data-collection phase is frozen at the requested milestone:

- **60,000 repository catalog** — completed;
- **1,267 deep-profile snapshots** — completed before the collection stop point;
- **697 weak-labelled snapshots** — available for experimental training;
- **250-row blinded human-review queue** — generated;
- **0 fabricated human reviews** — human validation remains genuinely independent;
- collection status: `stopped_at_requested_60k_catalog_milestone`.

Internal artifact filenames still contain `100k` because they are stable pipeline names created during the earlier scale design. Those filenames are retained for compatibility; they do **not** mean 100,000 repositories were collected.

### Diversity-first catalog sampling

The catalog collector partitions GitHub search by language, star bucket, creation year and archived vs active state. Partitions are interleaved so bounded runs do not consume one language or maintenance state first. Each stratum contributes at most the first 100 repositories, favoring breadth across many strata over depth inside one query.

### Deep-profile sampling

The deep manifest round-robins language and popularity strata and interleaves archived, recent-active and stale-active repositories. `pushed_at` is used only as a sampling proxy to improve the chance of collecting `watch` examples; it is never used as the training target.

### Collection safety

Collection was implemented as bounded, resumable GitHub Actions batches with checkpointing, rate-limit handling, monotonic progress checks and explicit failure when a batch attempts work but produces no new successful rows. Manifest changes preserve historical deep snapshots instead of deleting them.

The collection phase is now stopped. No catalog or deep batch should be triggered after the 60,000-repository milestone unless the project scope is deliberately reopened.

## Dataset unit and feature contract

One row = one repository at one point in time.

Model features:

- `days_since_last_commit`
- `bus_factor`
- `issue_closure_rate_pct`
- `pr_merge_rate_pct`
- `commits_90d`
- `contributors_sampled`
- `has_ci`
- `has_tests`

The current feature contract is versioned as `reposcope-risk-features-v1`. Training artifacts store both the ordered feature list and schema version. Inference fails closed when an artifact advertises an unsupported schema or mismatched feature list. Pre-versioned legacy artifacts are accepted only when their feature list matches v1 exactly.

Independent labeling evidence collected alongside the features:

- GitHub `archived` status;
- age of the latest GitHub release;
- latest release timestamp.

The deterministic RepoScope health score is **never used to create the ML label**.

## Weak-label policy

Current policy:

- GitHub explicitly marks the repository archived → `risky`;
- non-archived repository with latest release **150 days old or newer** → `healthy`;
- non-archived repository with latest release **180 days old or older** → `watch`;
- release age **151–179 days** → ambiguous and excluded from weak training;
- no independent release/archive evidence → excluded rather than guessed.

The review gap reduces boundary noise. Every accepted weak label records `label_source` and `label_evidence`.

## Human-review path

The independent reviewer protocol is defined in `docs/HUMAN_LABEL_RUBRIC.md`. Reviewers are blinded from the RepoScope health score, weak label and ML prediction so the human reference does not simply reproduce automation.

The queue and durable registry are intentionally separate:

- `data/repo_risk_human_review_queue.csv` is generated from ambiguous cases;
- `data/repo_risk_human_labels.csv` is durable and must contain real reviewer decisions only;
- allowed labels are exactly `healthy`, `watch` and `risky`;
- reviewer, notes and review timestamp can be stored for provenance;
- human review overrides a weak label for the same repository in the combined training set.

`scripts/compare_human_weak_labels.py` measures overlap, overall agreement, class-specific agreement and a weak-vs-human confusion matrix. It declares the comparison subset ready only once at least 60 weak/human overlaps exist and each human class has at least 10 examples.

## Dataset quality checks

`scripts/report_dataset_quality.py` reports catalog coverage, active/archive representation, language/license distribution, missingness, unique repository counts, class balance, label-source distribution and warnings for small or imbalanced classes and repeated snapshots. Raw row count is never treated as proof of data quality.

## Leakage controls and evaluation

Repository identity is the split unit. The same repository cannot occur on both sides of an evaluation split.

The training pipeline uses:

- **StratifiedGroupKFold** out-of-fold evaluation;
- an independent **GroupShuffleSplit** holdout;
- a chronological holdout using the newest repositories by `snapshot_at_utc` when the older partition contains all three classes;
- per-class precision, recall and F1;
- macro F1, accuracy and balanced accuracy;
- confusion matrices;
- feature importance and reproducibility metadata;
- final refit on all labelled rows only after isolated evaluation is complete.

## Probability reliability

Out-of-fold `predict_proba` values are used to measure multiclass log loss, multiclass Brier score, expected calibration error (ECE), mean confidence and calibration-bin summaries.

These values remain diagnostics. RepoScope does not present them as calibrated production confidence. Production-facing calibration stays blocked until independent human validation is sufficiently large.

## Failure-slice diagnostics

Out-of-fold predictions are checked across non-feature context including:

- language;
- repository size bucket;
- maintenance style.

Large slices with poor accuracy block promotion readiness. These checks are meant to surface where aggregate metrics hide systematic errors.

## Promotion readiness gate

`scripts/evaluate_model_readiness.py` writes a machine-readable readiness report. The policy requires:

- at least 1,000 deep snapshots;
- at least 50 labelled repositories in each risk class;
- grouped CV macro F1 ≥ 0.65;
- grouped CV balanced accuracy ≥ 0.65;
- temporal holdout with sufficient support for every class;
- temporal macro F1 ≥ 0.60;
- out-of-fold ECE ≤ 0.15;
- required failure-slice diagnostics with no large slice below the accuracy floor;
- a sufficiently large human/weak overlap;
- at least 10 human-reviewed examples in every class;
- weak/human agreement ≥ 0.70;
- no unresolved dataset-quality warnings.

The current generated readiness artifact is the source of truth. At the completed 60k scope, the remaining blocker is the independent human-reviewed validation subset.

Even after automated evidence passes, promotion is **not automatic**. The separate promotion record must receive an explicit manual approval.

## Model status

The dashboard identifies the model as **experimental weak supervision**. The deterministic health score remains the primary explainable signal. Scaled inference is protected by class-support, feature-schema, readiness and explicit-promotion gates.

## Promotion checklist

Before moving beyond experimental status, the project requires:

- a sufficiently large stratified human-reviewed validation subset;
- stable grouped and temporal metrics;
- acceptable probability reliability diagnostics;
- weak-label vs human-label comparison;
- inspected failure cases across language, repository size and maintenance style;
- no suspicious feature shortcut;
- reproducible data/model provenance;
- a manual promotion decision.

## Reproducibility artifacts

The current state is described by generated files rather than documentation guesses:

- `data/repo_risk_100k_progress.json`
- `data/repo_risk_100k_quality.json`
- `data/repo_risk_human_weak_comparison.json`
- `models/repo_risk_100k_metrics.json`
- `models/repo_risk_100k_model_card.md`
- `models/repo_risk_100k_readiness.json`
- `models/repo_risk_100k_promotion.json`

## Local evaluation commands

Collection commands are intentionally omitted from the normal continuation path because collection is frozen at 60,000 repositories. Existing artifacts can still be rebuilt or evaluated locally:

```bash
pip install -e ".[ml]"
python scripts/bootstrap_weak_labels.py --input data/repo_risk_unlabelled_100k.csv --output data/repo_risk_training_100k.csv
python scripts/export_label_review_queue.py --input data/repo_risk_unlabelled_100k.csv --output data/repo_risk_human_review_queue.csv --limit 250
python scripts/merge_human_labels.py --unlabelled data/repo_risk_unlabelled_100k.csv --weak data/repo_risk_training_100k.csv --human data/repo_risk_human_labels.csv --output data/repo_risk_training_combined_100k.csv
python scripts/compare_human_weak_labels.py --weak data/repo_risk_training_100k.csv --human data/repo_risk_human_labels.csv --output data/repo_risk_human_weak_comparison.json
python scripts/report_dataset_quality.py --catalog data/repository_catalog_100k.csv --training data/repo_risk_training_combined_100k.csv
python scripts/train_risk_model.py data/repo_risk_training_combined_100k.csv --output models/repo_risk_100k.joblib
python scripts/generate_model_card.py --progress data/repo_risk_100k_progress.json --quality data/repo_risk_100k_quality.json --metrics models/repo_risk_100k_metrics.json --output models/repo_risk_100k_model_card.md
python scripts/evaluate_model_readiness.py --progress data/repo_risk_100k_progress.json --quality data/repo_risk_100k_quality.json --metrics models/repo_risk_100k_metrics.json --human-comparison data/repo_risk_human_weak_comparison.json --output models/repo_risk_100k_readiness.json
```
