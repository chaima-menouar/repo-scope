# ML training strategy

RepoScope separates three forms of intelligence on purpose:

1. **Health score** — deterministic, explainable rules that work immediately.
2. **AI diagnosis** — structured evidence and recommendations, with an optional LLM enhancement.
3. **Experimental ML risk baseline** — a supervised Random Forest trained from collected repository snapshots.

The ML model is not presented as production ground truth. Its current labels are conservative **weak labels** built from maintenance evidence that is independent from the eight model features.

## Scale strategy

RepoScope separates broad discovery from expensive deep profiling:

- **100,000 repository catalog target** for broad coverage across language, age, popularity and maintenance states;
- **10,000 deep-profile target** for the more expensive feature extraction used by ML;
- bounded GitHub Actions batches so progress can be committed and resumed safely;
- generated progress and quality files are the source of truth for what has actually been collected.

A target is never presented as completed data until the generated artifacts verify it.

## Dataset unit

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

Independent labeling evidence collected alongside those features:

- GitHub `archived` status
- age of the latest GitHub release
- latest release timestamp

The existing health score is **never used to create the ML label**, which avoids simply training a model to imitate RepoScope's deterministic rules.

## Automated pipeline

The root workflow `.github/workflows/dataset.yml` performs the experimental pipeline:

1. incrementally build `data/repository_catalog_100k.csv`;
2. derive a deep-analysis manifest with active and archived representation;
3. collect deep repository snapshots into `data/repo_risk_unlabelled_100k.csv`;
4. apply conservative weak labels with `scripts/bootstrap_weak_labels.py`;
5. leave ambiguous repositories out of the training set;
6. generate `data/repo_risk_100k_quality.json`;
7. train only when enough labelled rows exist and the dataset changed;
8. write the model and evaluation metrics under `models/`;
9. commit progress so the next scheduled run resumes from durable state.

## Weak-label policy

Current policy:

- GitHub explicitly marks the repository archived → `risky`;
- repository is not archived and latest release is **150 days old or newer** → `healthy`;
- repository is not archived and latest release is **180 days old or older** → `watch`;
- release age from **151 to 179 days** → skipped as an ambiguous boundary case;
- no independent release/archive evidence → skipped rather than guessed.

This deliberate 29-day review gap reduces boundary noise. Every accepted weak label records `label_source` and `label_evidence`.

## Dataset quality checks

`scripts/report_dataset_quality.py` reports:

- catalog row count;
- active vs archived representation;
- language and license distribution;
- catalog-field missingness;
- training row and unique-repository counts;
- class distribution and class balance;
- label-source distribution;
- model-feature missingness;
- warnings for small classes, extreme imbalance, repeated repository snapshots and under-represented archived repositories.

These checks are not a replacement for human review, but they prevent the automated training path from treating raw row count as proof of data quality.

## Leakage controls and evaluation

RepoScope evaluates by repository identity rather than random rows. A repository cannot occur in both sides of a grouped split.

The training pipeline uses:

- **StratifiedGroupKFold** cross-validation when class support allows it;
- a separate **GroupShuffleSplit** holdout;
- per-class precision, recall and F1;
- macro F1 and accuracy for grouped cross-validation;
- train/test repository counts;
- class counts and label sources;
- feature importance;
- explicit warnings when the weakly-labelled dataset is too small or results look suspiciously optimistic.

A near-perfect score on a small weakly-labelled dataset is treated as a reason to investigate task simplicity or label artifacts, not as proof of production generalization.

## Model status

The dashboard identifies this model as **experimental weak supervision**. Its class probabilities are not described as calibrated production probabilities.

Production promotion would require a substantially larger independently reviewed human-labelled subset, failure-case analysis, calibration work, temporal validation and evidence that performance remains stable outside the repositories used during development.

## Local commands

```bash
pip install -e ".[ml]"
python scripts/collect_repository_catalog.py --target 100000 --max-new 5000
python scripts/collect_training_data.py --repos data/seed_repositories_100k.txt --output data/repo_risk_unlabelled_100k.csv --resume --limit 500
python scripts/bootstrap_weak_labels.py --input data/repo_risk_unlabelled_100k.csv --output data/repo_risk_training_100k.csv
python scripts/report_dataset_quality.py --catalog data/repository_catalog_100k.csv --training data/repo_risk_training_100k.csv
python scripts/train_risk_model.py data/repo_risk_training_100k.csv --output models/repo_risk_100k.joblib
```
