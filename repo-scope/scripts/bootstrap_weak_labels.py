from __future__ import annotations

import argparse
import csv
from pathlib import Path

from repo_scope.ml.labels import assign_weak_label


def build_training_csv(source: Path, output: Path) -> dict:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    labelled: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    for row in rows:
        assignment = assign_weak_label(row)
        if assignment is None:
            continue
        label, label_source, label_evidence = assignment
        enriched = dict(row)
        enriched["label"] = label
        enriched["label_source"] = label_source
        enriched["label_evidence"] = label_evidence
        labelled.append(enriched)
        counts[label] = counts.get(label, 0) + 1

    if len(counts) < 2:
        raise SystemExit("Weak-label bootstrap needs at least two evidence-backed classes.")

    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    for extra in ("label", "label_source", "label_evidence"):
        if extra not in fieldnames:
            fieldnames.append(extra)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(labelled)

    return {
        "input_rows": len(rows),
        "labelled_rows": len(labelled),
        "skipped_rows": len(rows) - len(labelled),
        "class_counts": counts,
        "label_policy": (
            "archived=>risky; release<=150d=>healthy; release>=180d=>watch; "
            "151-179d or no independent evidence=>skip"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an experimental weakly-labelled RepoScope training set.")
    parser.add_argument("--input", default="data/repo_risk_unlabelled.csv")
    parser.add_argument("--output", default="data/repo_risk_training.csv")
    args = parser.parse_args()
    result = build_training_csv(Path(args.input), Path(args.output))
    print(result)


if __name__ == "__main__":
    main()
