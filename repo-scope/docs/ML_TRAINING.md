# ML training strategy

RepoScope separates three forms of intelligence on purpose:

1. **Health score** — deterministic, explainable rules that work immediately.
2. **AI diagnosis** — structured evidence and recommendations, with an optional LLM enhancement.
3. **Experimental ML risk baseline** — a supervised Random Forest trained from collected repository snapshots.

The ML model is not presented as production ground truth. Its current labels are conservative **weak labels** built from maintenance evidence that is independent from the eight model features.

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

## Automated bootstrap

The root workflow `.github/workflows/dataset.yml` performs the experimental pipeline:

1. analyze a diverse seed list of public repositories;
2. write `data/repo_risk_unlabelled.csv`;
3. apply conservative weak labels with `scripts/bootstrap_weak_labels.py`;
4. leave repositories without independent evidence out of the training set;
5. train the Random Forest with a repository-group split;
6. write the model to `models/repo_risk.joblib`;
7. write evaluation output to `models/repo_risk_metrics.json`.

Current weak-label policy:

- GitHub explicitly marks the repository archived → `risky`;
- repository is not archived and latest release is at most 180 days old → `healthy`;
- repository is not archived and latest release is older than 180 days → `watch`;
- no independent release/archive evidence → skipped rather than guessed.

This policy is intentionally conservative and is recorded in the training CSV through `label_source` and `label_evidence`.

## Leakage controls

RepoScope splits by repository identity rather than random rows. A repository cannot occur in both train and test sets. The training code also uses a deterministic random seed and refuses to train if the train split contains fewer than two classes.

## Evaluation

The training output includes:

- per-class precision, recall and F1;
- train/test repository counts;
- class names;
- feature importance;
- split strategy and random seed.

The dashboard identifies this model as **experimental weak supervision**. Its class probabilities are not described as calibrated production probabilities.

## Local commands

```bash
pip install -e ".[ml]"
python scripts/collect_training_data.py
python scripts/bootstrap_weak_labels.py
python scripts/train_risk_model.py data/repo_risk_training.csv --output models/repo_risk.joblib
```

For a future production-grade model, replace weak labels with a larger independently reviewed human-labelled dataset, inspect calibration and failure cases, and only then promote model probabilities to a production risk signal.
