from __future__ import annotations

import argparse
import json
from pathlib import Path


def _json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value, default="n/a") -> str:
    return default if value is None else str(value)


def _matrix_lines(section: dict) -> str:
    labels = section.get("labels") or []
    matrix = section.get("confusion_matrix") or []
    if not labels or not matrix:
        return "Not available."
    header = "| actual \\ predicted | " + " | ".join(labels) + " |"
    divider = "| --- | " + " | ".join("---:" for _ in labels) + " |"
    rows = []
    for label, values in zip(labels, matrix, strict=False):
        rows.append("| " + label + " | " + " | ".join(str(value) for value in values) + " |")
    return "\n".join([header, divider, *rows])


def build_model_card(progress_path: Path, quality_path: Path, metrics_path: Path) -> str:
    progress = _json(progress_path)
    quality = _json(quality_path)
    metrics = _json(metrics_path)
    training_quality = quality.get("training", {})
    cv = metrics.get("cross_validation", {})
    heldout = metrics.get("heldout", {})
    temporal = metrics.get("temporal_holdout", {})
    calibration = metrics.get("calibration", {})

    warning = metrics.get("evaluation_warning") or "No automated evaluation warning was emitted."
    quality_warnings = quality.get("warnings") or []
    quality_warning_text = "\n".join(f"- {item}" for item in quality_warnings) or "- None reported by the automated dataset-quality checks."

    labels = training_quality.get("labels", {})
    label_lines = "\n".join(f"- `{label}`: {count}" for label, count in labels.items()) or "- Not available yet."
    sources = training_quality.get("label_sources", {})
    source_lines = "\n".join(f"- `{source}`: {count}" for source, count in sources.items()) or "- Not available yet."

    temporal_text = (
        f"- Available: yes\n"
        f"- Strategy: {_fmt(temporal.get('strategy'))}\n"
        f"- Cutoff UTC: {_fmt(temporal.get('cutoff_utc'))}\n"
        f"- Balanced accuracy: {_fmt(temporal.get('balanced_accuracy'))}\n"
        f"- Macro F1: {_fmt(temporal.get('macro_f1'))}\n"
        f"- Missing test classes: {_fmt(temporal.get('missing_test_classes'), '[]')}"
        if temporal.get("available")
        else f"- Available: no\n- Reason: {_fmt(temporal.get('reason'))}"
    )

    return f"""# RepoScope Risk Model Card

> Status: **experimental weak supervision**. This model is a secondary research signal, not a calibrated production risk score.

## Intended use

RepoScope uses this model to explore whether repository-maintenance risk can be learned from engineering signals that are separate from the deterministic health score. The deterministic score remains the primary explainable signal.

## Data snapshot

- Catalog target: {_fmt(progress.get('catalog_target'))}
- Catalog repositories collected: {_fmt(progress.get('catalog_repositories'))}
- Deep-profile target: {_fmt(progress.get('deep_profile_target'))}
- Deep snapshots collected: {_fmt(progress.get('deep_snapshots'))}
- Labelled snapshots: {_fmt(progress.get('labelled_snapshots'))}
- Human-review queue: {_fmt(progress.get('human_review_queue'))}
- Training repositories in latest model: {_fmt(metrics.get('repositories'))}

### Label distribution

{label_lines}

### Label provenance

{source_lines}

Weak labels are based on independent GitHub maintenance evidence. RepoScope's deterministic health score is never used as the training target.

## Model and reproducibility

- Model: {_fmt(metrics.get('model_type'))}
- Feature schema: `{_fmt(metrics.get('feature_schema_version'))}`
- Artifact fit strategy: {_fmt(metrics.get('artifact_fit_strategy'))}
- Source CSV: `{_fmt(metrics.get('source_csv'))}`
- Dataset SHA-256: `{_fmt(metrics.get('dataset_sha256'))}`
- Trained at UTC: {_fmt(metrics.get('trained_at_utc'))}
- scikit-learn: {_fmt(metrics.get('scikit_learn_version'))}

## Evaluation

- Cross-validation strategy: {_fmt(cv.get('strategy'))}
- Cross-validation folds: {_fmt(cv.get('folds'))}
- Cross-validation accuracy: {_fmt(cv.get('accuracy'))}
- Cross-validation balanced accuracy: {_fmt(cv.get('balanced_accuracy'))}
- Cross-validation macro F1: {_fmt(cv.get('macro_f1'))}
- Grouped holdout train repositories: {_fmt(metrics.get('train_repositories'))}
- Grouped holdout test repositories: {_fmt(metrics.get('test_repositories'))}
- Holdout accuracy: {_fmt(heldout.get('accuracy'))}
- Holdout balanced accuracy: {_fmt(heldout.get('balanced_accuracy'))}
- Holdout macro F1: {_fmt(heldout.get('macro_f1'))}

### Temporal holdout

{temporal_text}

### Probability calibration diagnostics

- Status: {_fmt(calibration.get('status'))}
- Source: {_fmt(calibration.get('source'))}
- Log loss: {_fmt(calibration.get('log_loss'))}
- Multiclass Brier score: {_fmt(calibration.get('multiclass_brier_score'))}
- Expected calibration error (10 bins): {_fmt(calibration.get('expected_calibration_error_10_bin'))}
- Mean confidence: {_fmt(calibration.get('mean_confidence'))}

The probability diagnostics are measured from repository-grouped out-of-fold predictions. They are diagnostic evidence only; RepoScope does not describe the probabilities as calibrated confidence until independent human-reviewed validation supports that claim.

### Cross-validation confusion matrix

{_matrix_lines(cv)}

### Grouped holdout confusion matrix

{_matrix_lines(heldout)}

### Temporal holdout confusion matrix

{_matrix_lines(temporal) if temporal.get('available') else 'Not available.'}

### Automated evaluation warning

{warning}

### Dataset-quality warnings

{quality_warning_text}

## Known limitations

- Current automated training targets are dominated by weak labels until the durable human-review registry grows.
- Archive/release evidence may encode a simpler maintenance concept than real engineering risk.
- Probability diagnostics do not equal production calibration.
- GitHub API features are sampled and rate-limited rather than exhaustive history.
- Performance must be confirmed on an independently reviewed human-labelled subset before any production promotion.

## Promotion requirements

The model stays experimental until the project has meaningful class support, human-reviewed labels, stable repository-grouped cross-validation, a valid temporal holdout, acceptable calibration diagnostics and documented failure-case review. The generated readiness report remains the machine-readable gate; passing it still requires a manual promotion decision.

This file is generated from RepoScope's committed progress, quality and metrics artifacts so it should not claim collection or performance numbers that those artifacts do not contain.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a truthful model card from RepoScope ML artifacts.")
    parser.add_argument("--progress", default="data/repo_risk_100k_progress.json")
    parser.add_argument("--quality", default="data/repo_risk_100k_quality.json")
    parser.add_argument("--metrics", default="models/repo_risk_100k_metrics.json")
    parser.add_argument("--output", default="models/repo_risk_100k_model_card.md")
    args = parser.parse_args()
    card = build_model_card(Path(args.progress), Path(args.quality), Path(args.metrics))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(card, encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
