# ML training strategy

RepoScope separates three forms of intelligence on purpose:

1. **Health score** — deterministic, explainable rules that work immediately.
2. **AI diagnosis** — structured evidence and recommendations, with an optional LLM enhancement.
3. **Experimental ML risk baseline** — a supervised Random Forest trained from collected repository snapshots.

The ML model is not presented as production ground truth. Its current labels are conservative **weak labels** built from maintenance evidence that is independent from the eight model features, with a separate durable path for independent human review.

## Scale strategy

RepoScope separates broad discovery from expensive deep profiling:

- **100,000 repository catalog target** for broad coverage across language, age, popularity and maintenance states;
- **10,000 deep-profile target** for the more expensive feature extraction used by ML;
- bounded GitHub Actions batches so progress can be committed and resumed safely;
- generated progress and quality files are the source of truth for what has actually been collected.

A target is never presented as completed data until the generated artifacts verify it.

### Diversity-first catalog sampling

The catalog collector partitions GitHub search by language, star bucket, creation year and archived vs active state. Partitions are interleaved so a bounded run does not consume one language or maintenance state first. Each stratum contributes at most the first **100 repositories**, favoring breadth across many strata over depth inside one query.

### Deep-profile sampling

The deep manifest round-robins language and popularity strata and interleaves archived, recent-active and stale-active repositories. `pushed_at` is used only as a sampling proxy to improve the chance of collecting `watch` examples; it is never used as the training target.

### API-efficient collection and branch-safe continuation

The ML collector reuses catalog metadata and omits API calls for fields that are not part of the feature vector. The workflow currently collects up to **130 deep repositories per batch**, uses six workers and checkpoints every 25 successful repositories.

GitHub scheduled workflows are tied to the default branch, while this work remains intentionally isolated on `improve/portfolio-ai-cloud`. To keep collection progressing without merging or deploying, `.github/dataset-trigger.txt` is a branch-safe trigger. The RepoScope watcher updates it only after the previous dataset run has completed and either the 100k catalog or 10k deep-profile target is still incomplete. This creates exactly one new bounded batch at a time and avoids overlapping runs.

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

## Automated pipeline

The root workflow `.github/workflows/dataset.yml` performs the experimental pipeline:

1. incrementally advance `data/repository_catalog_100k.csv`;
2. derive a diverse 10k deep-analysis manifest;
3. collect resumable deep snapshots into `data/repo_risk_unlabelled_100k.csv`;
4. apply conservative weak labels;
5. export ambiguous cases to `data/repo_risk_human_review_queue.csv`;
6. merge durable human labels from `data/repo_risk_human_labels.csv`;
7. generate `data/repo_risk_human_weak_comparison.json`;
8. generate dataset-quality diagnostics;
9. train only at meaningful milestones and only when all three classes have minimum support;
10. evaluate grouped cross-validation, grouped holdout, temporal holdout and out-of-fold calibration diagnostics;
11. write model metadata and a generated Model Card;
12. generate `models/repo_risk_100k_readiness.json` with explicit promotion blockers;
13. commit durable progress so the next bounded run resumes safely.

## Weak-label policy

Current policy:

- GitHub explicitly marks the repository archived → `risky`;
- non-archived repository with latest release **150 days old or newer** → `healthy`;
- non-archived repository with latest release **180 days old or older** → `watch`;
- release age **151–179 days** → ambiguous and excluded from weak training;
- no independent release/archive evidence → excluded rather than guessed.

The 29-day review gap reduces boundary noise. Every accepted weak label records `label_source` and `label_evidence`.

## Human-review path

The independent reviewer protocol is defined in `docs/HUMAN_LABEL_RUBRIC.md`. Reviewers are blinded from the RepoScope health score, weak label and ML prediction so the human reference does not simply reproduce automation.

The queue and durable registry are intentionally separate:

- `data/repo_risk_human_review_queue.csv` is regenerated by automation;
- `data/repo_risk_human_labels.csv` is durable and is never regenerated from the queue;
- allowed labels are exactly `healthy`, `watch` and `risky`;
- reviewer, notes and review timestamp can be stored for provenance;
- human review overrides a weak label for the same repository in the combined training set.

`scripts/compare_human_weak_labels.py` measures overlap, overall agreement, class-specific agreement and a weak-vs-human confusion matrix. It only declares the comparison subset ready once at least 60 weak/human overlaps exist and each human class has at least 10 examples.

## Dataset quality checks

`scripts/report_dataset_quality.py` reports catalog coverage, active/archive representation, language/license distribution, missingness, unique repository counts, class balance, label-source distribution and warnings for small or imbalanced classes and repeated snapshots. Raw row count is never treated as proof of data quality.

## Leakage controls and evaluation

Repository identity is the split unit. The same repository cannot occur on both sides of an evaluation split.

The training pipeline uses:

- **StratifiedGroupKFold** out-of-fold evaluation;
- an independent **GroupShuffleSplit** holdout;
- a chronological holdout using the newest 25% of repositories by `snapshot_at_utc` when the older partition contains all three classes;
- per-class precision, recall and F1;
- macro F1, accuracy and balanced accuracy;
- confusion matrices;
- feature importance and reproducibility metadata;
- final refit on all labelled rows only **after** isolated evaluation is complete.

### Probability reliability

Out-of-fold `predict_proba` values are used to measure:

- multiclass log loss;
- multiclass Brier score;
- 10-bin expected calibration error (ECE);
- mean confidence and calibration-bin accuracy/confidence summaries.

These values are diagnostics. The artifact metadata deliberately says `uncalibrated_analysis_only`; RepoScope does not call them calibrated confidence scores. Actual production-facing calibration remains blocked until the independent human-reviewed validation set is sufficiently large.

## Promotion readiness gate

`scripts/evaluate_model_readiness.py` writes a machine-readable readiness report. Automated promotion remains blocked unless all of these are true:

- at least 1,000 deep snapshots;
- at least 50 labelled repositories in each risk class;
- grouped CV macro F1 ≥ 0.65;
- grouped CV balanced accuracy ≥ 0.65;
- temporal holdout exists, includes all three classes and macro F1 ≥ 0.60;
- out-of-fold ECE ≤ 0.15;
- human/weak overlap is large enough for comparison;
- weak/human agreement ≥ 0.70;
- dataset-quality report has no unresolved warnings.

Even when every automated gate passes, the report says `eligible_for_manual_review`, not “production ready.” Promotion still requires a deliberate human decision.

## Model status

The dashboard identifies the model as **experimental weak supervision**. Scaled inference is additionally protected by class-support and feature-schema gates. If the scaled artifact is not eligible, RepoScope falls back to the verified legacy experimental baseline.

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

Until then, the deterministic health score remains the primary explainable signal and ML remains a secondary experimental signal.

## Local commands

```bash
pip install -e ".[ml]"
python scripts/collect_repository_catalog.py --target 100000 --output data/repository_catalog_100k.csv --state data/repository_catalog_100k.state.json --max-new 5000
python scripts/build_deep_manifest.py --catalog data/repository_catalog_100k.csv --output data/seed_repositories_100k.txt --target 10000 --archived-fraction 0.20 --stale-active-fraction 0.35
python scripts/collect_training_data.py --repos data/seed_repositories_100k.txt --catalog data/repository_catalog_100k.csv --output data/repo_risk_unlabelled_100k.csv --workers 6 --resume --limit 130 --checkpoint-every 25
python scripts/bootstrap_weak_labels.py --input data/repo_risk_unlabelled_100k.csv --output data/repo_risk_training_100k.csv
python scripts/export_label_review_queue.py --input data/repo_risk_unlabelled_100k.csv --output data/repo_risk_human_review_queue.csv --limit 250
python scripts/merge_human_labels.py --unlabelled data/repo_risk_unlabelled_100k.csv --weak data/repo_risk_training_100k.csv --human data/repo_risk_human_labels.csv --output data/repo_risk_training_combined_100k.csv
python scripts/compare_human_weak_labels.py --weak data/repo_risk_training_100k.csv --human data/repo_risk_human_labels.csv --output data/repo_risk_human_weak_comparison.json
python scripts/report_dataset_quality.py --catalog data/repository_catalog_100k.csv --training data/repo_risk_training_combined_100k.csv
python scripts/train_risk_model.py data/repo_risk_training_combined_100k.csv --output models/repo_risk_100k.joblib
python scripts/generate_model_card.py --progress data/repo_risk_100k_progress.json --quality data/repo_risk_100k_quality.json --metrics models/repo_risk_100k_metrics.json --output models/repo_risk_100k_model_card.md
python scripts/evaluate_model_readiness.py --progress data/repo_risk_100k_progress.json --quality data/repo_risk_100k_quality.json --metrics models/repo_risk_100k_metrics.json --human-comparison data/repo_risk_human_weak_comparison.json --output models/repo_risk_100k_readiness.json
```
