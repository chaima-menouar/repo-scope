# ML training strategy

RepoScope separates three forms of intelligence on purpose:

1. **Health score** — deterministic, explainable rules that work immediately.
2. **AI diagnosis** — structured evidence and recommendations, with an optional LLM enhancement.
3. **Experimental ML risk baseline** — a supervised Random Forest trained from collected repository snapshots.

The ML model is not presented as production ground truth. Its current labels are conservative **weak labels** built from maintenance evidence that is independent from the eight model features, with a separate durable path for optional human review.

## Scale strategy

RepoScope separates broad discovery from expensive deep profiling:

- **100,000 repository catalog target** for broad coverage across language, age, popularity and maintenance states;
- **10,000 deep-profile target** for the more expensive feature extraction used by ML;
- bounded GitHub Actions batches so progress can be committed and resumed safely;
- generated progress and quality files are the source of truth for what has actually been collected.

A target is never presented as completed data until the generated artifacts verify it.

### Diversity-first catalog sampling

The catalog collector partitions GitHub search by:

- language;
- star bucket;
- creation year;
- archived vs active state.

Partitions are interleaved so a bounded run does not consume one language or maintenance state first. Each stratum contributes at most the first **100 repositories** instead of walking up to GitHub's 1,000-search-result ceiling for that query. This intentionally favors breadth across many strata over depth inside one stratum.

### Deep-profile sampling

The deep manifest is built separately from the catalog. It round-robins language and popularity strata and interleaves:

- archived repositories;
- recent active repositories;
- stale active repositories, based only on `pushed_at` as a **sampling proxy**.

The stale-active proxy is never used as a training target. It only improves the chance of collecting enough independently labelled `watch` examples without leaking the weak-label rule into the model feature vector.

### API-efficient deep collection

The ML collector reuses repository metadata that already exists in the catalog instead of requesting it again. It also omits the languages endpoint because language bytes are not one of the eight ML features. Deep snapshots therefore need roughly six core REST calls instead of the full interactive profile's larger request set.

The Actions workflow currently uses a conservative batch size of **130 repositories** with six workers and one GitHub API page per sampled endpoint. Checkpoints are written every 25 successful repositories.

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

The current feature contract is versioned as `reposcope-risk-features-v1`. The training artifact stores both the ordered feature list and the schema version. Inference fails closed when an artifact advertises an unsupported schema or a mismatched feature list. Pre-versioned legacy artifacts are accepted only when their feature list matches v1 exactly.

Independent labeling evidence collected alongside those features:

- GitHub `archived` status
- age of the latest GitHub release
- latest release timestamp

The existing health score is **never used to create the ML label**, which avoids simply training a model to imitate RepoScope's deterministic rules.

## Automated pipeline

The root workflow `.github/workflows/dataset.yml` performs the experimental pipeline:

1. incrementally build `data/repository_catalog_100k.csv`;
2. derive a diverse deep-analysis manifest with active, archived and stale-active representation;
3. collect deep repository snapshots into `data/repo_risk_unlabelled_100k.csv` using catalog metadata to reduce API cost;
4. apply conservative weak labels with `scripts/bootstrap_weak_labels.py`;
5. leave ambiguous repositories out of the weak training set and export them to `data/repo_risk_human_review_queue.csv`;
6. merge optional durable human reviews from `data/repo_risk_human_labels.csv` into `data/repo_risk_training_combined_100k.csv`;
7. generate `data/repo_risk_100k_quality.json` from the combined training set;
8. train only when all three classes have at least 20 repositories and the retraining milestone is reached;
9. write the model, evaluation metrics and generated model card under `models/`;
10. commit progress so the next eligible workflow run resumes from durable state.

## Weak-label policy

Current policy:

- GitHub explicitly marks the repository archived → `risky`;
- repository is not archived and latest release is **150 days old or newer** → `healthy`;
- repository is not archived and latest release is **180 days old or older** → `watch`;
- release age from **151 to 179 days** → skipped as an ambiguous boundary case;
- no independent release/archive evidence → skipped rather than guessed.

This deliberate 29-day review gap reduces boundary noise. Every accepted weak label records `label_source` and `label_evidence`.

## Human-review path

The independent reviewer protocol is defined in `docs/HUMAN_LABEL_RUBRIC.md`. Reviewers are blinded from RepoScope's health score, weak label and ML output so human labels do not simply reproduce the automated rules.

The generated review queue and durable human labels are deliberately separate:

- `data/repo_risk_human_review_queue.csv` is regenerated by automation and is only a list of candidates to inspect;
- `data/repo_risk_human_labels.csv` is the durable review registry and is never regenerated from the queue;
- allowed human labels are exactly `healthy`, `watch` and `risky`;
- `review_notes`, `reviewer` and `reviewed_at_utc` can be recorded for provenance;
- `scripts/merge_human_labels.py` merges human reviews with the weak-labelled set;
- a human-reviewed label overrides a weak label for the same repository and records `label_source=human_review`.

Keeping those files separate prevents workflow regeneration from erasing manual review work and makes corrections to weak labels auditable.

## Dataset quality checks

`scripts/report_dataset_quality.py` reports:

- catalog row count;
- active vs archived representation;
- language and license distribution;
- catalog-field missingness;
- training row and unique-repository counts;
- class distribution and class balance;
- label-source distribution, including human review when present;
- model-feature missingness;
- warnings for small classes, extreme imbalance, repeated repository snapshots and under-represented archived repositories.

These checks are not a replacement for human review, but they prevent the automated training path from treating raw row count as proof of data quality.

## Leakage controls and evaluation

RepoScope evaluates by repository identity rather than random rows. A repository cannot occur in both sides of a grouped split.

The training pipeline uses:

- **StratifiedGroupKFold** cross-validation when class support allows it;
- a separate **GroupShuffleSplit** holdout;
- per-class precision, recall and F1;
- macro F1, raw accuracy and **balanced accuracy**;
- confusion matrices for both grouped cross-validation and holdout evaluation;
- train/test repository counts;
- class counts and label sources;
- feature importance;
- explicit warnings when the weakly-labelled dataset is too small, minority-class performance is weak, or results look suspiciously optimistic.

Balanced accuracy and confusion matrices are first-class outputs because raw accuracy can look excellent while a minority class is effectively ignored.

A near-perfect score on a small weakly-labelled dataset is treated as a reason to investigate task simplicity or label artifacts, not as proof of production generalization.

## Model status

The dashboard identifies this model as **experimental weak supervision**. Its class probabilities are not described as calibrated production probabilities.

The scaled artifact is only eligible for default inference after all three classes have meaningful support. Otherwise RepoScope safely falls back to the verified legacy experimental baseline.

## Promotion checklist

The model should only move beyond `experimental_weak_supervision` after all of the following are satisfied:

- a large deep-profile dataset with meaningful representation of every class;
- a stratified human-reviewed label subset independent of the weak-label rules;
- grouped cross-validation that remains stable across folds;
- a repository-grouped holdout with no identity leakage;
- a temporal holdout using repositories/snapshots newer than the training cutoff;
- per-class precision, recall and F1 reviewed, not accuracy alone;
- balanced accuracy and confusion matrices reviewed for minority-class collapse;
- calibration measured before exposing probability-like scores as confidence;
- failure cases inspected across language, repository size and maintenance style;
- weak-label and human-label performance compared separately;
- feature importance checked for suspicious shortcuts;
- reproducible model/data provenance recorded in the artifact metadata.

Until then, RepoScope keeps the deterministic health score as the primary explainable signal and the ML output as an experimental secondary signal.

## Local commands

```bash
pip install -e ".[ml]"
python scripts/collect_repository_catalog.py --target 100000 --output data/repository_catalog_100k.csv --state data/repository_catalog_100k.state.json --max-new 5000
python scripts/build_deep_manifest.py --catalog data/repository_catalog_100k.csv --output data/seed_repositories_100k.txt --target 10000 --archived-fraction 0.20 --stale-active-fraction 0.35
python scripts/collect_training_data.py --repos data/seed_repositories_100k.txt --catalog data/repository_catalog_100k.csv --output data/repo_risk_unlabelled_100k.csv --workers 6 --resume --limit 130 --checkpoint-every 25
python scripts/bootstrap_weak_labels.py --input data/repo_risk_unlabelled_100k.csv --output data/repo_risk_training_100k.csv
python scripts/export_label_review_queue.py --input data/repo_risk_unlabelled_100k.csv --output data/repo_risk_human_review_queue.csv --limit 250
python scripts/merge_human_labels.py --unlabelled data/repo_risk_unlabelled_100k.csv --weak data/repo_risk_training_100k.csv --human data/repo_risk_human_labels.csv --output data/repo_risk_training_combined_100k.csv
python scripts/report_dataset_quality.py --catalog data/repository_catalog_100k.csv --training data/repo_risk_training_combined_100k.csv
python scripts/train_risk_model.py data/repo_risk_training_combined_100k.csv --output models/repo_risk_100k.joblib
python scripts/generate_model_card.py --progress data/repo_risk_100k_progress.json --quality data/repo_risk_100k_quality.json --metrics models/repo_risk_100k_metrics.json --output models/repo_risk_100k_model_card.md
```
