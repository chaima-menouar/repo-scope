from __future__ import annotations

import argparse
import csv
from pathlib import Path

from repo_scope.ml.training import EXPECTED_LABELS

HUMAN_COLUMNS = ["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"]


def load_human_labels(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    labels: dict[str, dict[str, str]] = {}
    for row in rows:
        repo = (row.get("repo") or "").strip()
        label = (row.get("human_label") or "").strip()
        if not repo and not label:
            continue
        if not repo:
            raise ValueError("Every human-reviewed row must include a repository.")
        if label not in EXPECTED_LABELS:
            raise ValueError(
                f"Human label for {repo} must be one of {', '.join(sorted(EXPECTED_LABELS))}; got {label!r}."
            )
        labels[repo] = {
            "human_label": label,
            "review_notes": (row.get("review_notes") or "").strip(),
            "reviewer": (row.get("reviewer") or "").strip(),
            "reviewed_at_utc": (row.get("reviewed_at_utc") or "").strip(),
        }
    return labels


def merge_labels(
    unlabelled_path: Path,
    weak_training_path: Path,
    human_labels_path: Path,
    output_path: Path,
) -> dict[str, object]:
    with unlabelled_path.open(encoding="utf-8", newline="") as handle:
        source_rows = {row["repo"]: row for row in csv.DictReader(handle) if row.get("repo")}
    with weak_training_path.open(encoding="utf-8", newline="") as handle:
        weak_rows = {row["repo"]: row for row in csv.DictReader(handle) if row.get("repo")}

    human_labels = load_human_labels(human_labels_path)
    unknown = sorted(set(human_labels) - set(source_rows))
    if unknown:
        raise ValueError("Human labels reference repositories absent from the snapshot dataset: " + ", ".join(unknown))

    combined = dict(weak_rows)
    overridden = 0
    added = 0
    for repo, review in human_labels.items():
        base = dict(source_rows[repo])
        if repo in combined:
            overridden += 1
        else:
            added += 1
        base["label"] = review["human_label"]
        base["label_source"] = "human_review"
        evidence_parts = []
        if review["reviewer"]:
            evidence_parts.append(f"reviewer={review['reviewer']}")
        if review["reviewed_at_utc"]:
            evidence_parts.append(f"reviewed_at_utc={review['reviewed_at_utc']}")
        if review["review_notes"]:
            evidence_parts.append(f"notes={review['review_notes']}")
        base["label_evidence"] = "; ".join(evidence_parts) or "human-reviewed label"
        combined[repo] = base

    ordered = [combined[repo] for repo in source_rows if repo in combined]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_fieldnames = list(next(iter(source_rows.values())).keys()) if source_rows else []
    fieldnames = list(source_fieldnames)
    for column in ("label", "label_source", "label_evidence"):
        if column not in fieldnames:
            fieldnames.append(column)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ordered)

    class_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for row in ordered:
        label = row.get("label", "")
        source = row.get("label_source", "")
        class_counts[label] = class_counts.get(label, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1

    return {
        "rows": len(ordered),
        "human_reviews": len(human_labels),
        "human_added": added,
        "weak_labels_overridden": overridden,
        "class_counts": class_counts,
        "label_sources": source_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge durable human RepoScope labels with weak-label training data.")
    parser.add_argument("--unlabelled", default="data/repo_risk_unlabelled_100k.csv")
    parser.add_argument("--weak", default="data/repo_risk_training_100k.csv")
    parser.add_argument("--human", default="data/repo_risk_human_labels.csv")
    parser.add_argument("--output", default="data/repo_risk_training_combined_100k.csv")
    args = parser.parse_args()
    result = merge_labels(
        Path(args.unlabelled),
        Path(args.weak),
        Path(args.human),
        Path(args.output),
    )
    print(result)


if __name__ == "__main__":
    main()
