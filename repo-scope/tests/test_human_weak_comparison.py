from __future__ import annotations

import csv

from scripts.compare_human_weak_labels import build_report


def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_human_weak_report_measures_overlap_and_agreement(tmp_path):
    weak = tmp_path / "weak.csv"
    human = tmp_path / "human.csv"
    _write_csv(
        weak,
        ["repo", "label"],
        [
            {"repo": "org/a", "label": "healthy"},
            {"repo": "org/b", "label": "watch"},
            {"repo": "org/c", "label": "risky"},
        ],
    )
    _write_csv(
        human,
        ["repo", "human_label"],
        [
            {"repo": "org/a", "human_label": "healthy"},
            {"repo": "org/b", "human_label": "risky"},
            {"repo": "org/d", "human_label": "watch"},
        ],
    )

    report = build_report(weak, human)
    assert report["overlap_repositories"] == 2
    assert report["human_only_repositories"] == 1
    assert report["agreement_count"] == 1
    assert report["agreement_rate"] == 0.5
    assert report["status"] == "insufficient_human_review"
    assert report["confusion_matrix_weak_rows_human_columns"][0][0] == 1
    assert report["confusion_matrix_weak_rows_human_columns"][1][2] == 1
