from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from repo_scope.ml.training import LABEL_ORDER


def build_report(weak_path: Path, human_path: Path) -> dict:
    weak_rows = {}
    if weak_path.exists() and weak_path.stat().st_size:
        with weak_path.open(encoding="utf-8", newline="") as handle:
            weak_rows = {
                (row.get("repo") or "").strip(): (row.get("label") or "").strip()
                for row in csv.DictReader(handle)
                if (row.get("repo") or "").strip() and (row.get("label") or "").strip()
            }

    human_rows = {}
    if human_path.exists() and human_path.stat().st_size:
        with human_path.open(encoding="utf-8", newline="") as handle:
            human_rows = {
                (row.get("repo") or "").strip(): (row.get("human_label") or "").strip()
                for row in csv.DictReader(handle)
                if (row.get("repo") or "").strip() and (row.get("human_label") or "").strip()
            }

    overlap = sorted(set(weak_rows) & set(human_rows))
    human_only = sorted(set(human_rows) - set(weak_rows))
    agreements = sum(1 for repo in overlap if weak_rows[repo] == human_rows[repo])
    matrix = [[0 for _ in LABEL_ORDER] for _ in LABEL_ORDER]
    by_weak = {label: {"reviewed": 0, "agreed": 0} for label in LABEL_ORDER}

    for repo in overlap:
        weak_label = weak_rows[repo]
        human_label = human_rows[repo]
        if weak_label in LABEL_ORDER and human_label in LABEL_ORDER:
            matrix[LABEL_ORDER.index(weak_label)][LABEL_ORDER.index(human_label)] += 1
            by_weak[weak_label]["reviewed"] += 1
            if weak_label == human_label:
                by_weak[weak_label]["agreed"] += 1

    for values in by_weak.values():
        reviewed = values["reviewed"]
        values["agreement_rate"] = round(values["agreed"] / reviewed, 6) if reviewed else None

    human_counts = Counter(human_rows.values())
    minimum_human_class = min((human_counts.get(label, 0) for label in LABEL_ORDER), default=0)
    status = "ready_for_comparison" if len(overlap) >= 60 and minimum_human_class >= 10 else "insufficient_human_review"

    return {
        "status": status,
        "weak_labelled_repositories": len(weak_rows),
        "human_reviewed_repositories": len(human_rows),
        "overlap_repositories": len(overlap),
        "human_only_repositories": len(human_only),
        "agreement_count": agreements,
        "agreement_rate": round(agreements / len(overlap), 6) if overlap else None,
        "labels": LABEL_ORDER,
        "confusion_matrix_weak_rows_human_columns": matrix,
        "agreement_by_weak_label": by_weak,
        "human_class_counts": {label: int(human_counts.get(label, 0)) for label in LABEL_ORDER},
        "minimum_requirement": {
            "overlap_repositories": 60,
            "human_repositories_per_class": 10,
        },
        "note": (
            "This report treats human review as the independent reference for measuring weak-label agreement. "
            "It does not promote the model by itself."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare RepoScope weak labels with durable human reviews.")
    parser.add_argument("--weak", default="data/repo_risk_training_100k.csv")
    parser.add_argument("--human", default="data/repo_risk_human_labels.csv")
    parser.add_argument("--output", default="data/repo_risk_human_weak_comparison.json")
    args = parser.parse_args()
    report = build_report(Path(args.weak), Path(args.human))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
