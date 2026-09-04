# ML training strategy

RepoScope's rule-based health score is intentionally usable before machine learning. A supervised model is only meaningful after we have real labelled repository snapshots.

## Dataset unit

One row = one repository at one point in time.

Features exported today:

- `days_since_last_commit`
- `bus_factor`
- `issue_closure_rate_pct`
- `pr_merge_rate_pct`
- `commits_90d`
- `contributors_sampled`
- `has_ci`
- `has_tests`

The `label` must be assigned using a documented human rubric rather than derived from the existing health score; otherwise the model would merely learn to copy our rules.

## Minimum workflow

1. Collect snapshots from varied languages, sizes and organizations.
2. Label them independently using maintenance evidence.
3. Split repositories, not rows, across train/test to reduce leakage.
4. Start with an interpretable baseline and Random Forest.
5. Measure per-class precision/recall/F1 and calibration.
6. Inspect feature importance and failure cases.
7. Only then expose `risk_probability` in the API.

## Commands

```bash
pip install -e ".[ml]"
python scripts/export_training_row.py owner/repo --label healthy
python scripts/train_risk_model.py data/repo_risk_training.csv --output models/repo_risk.joblib
```
