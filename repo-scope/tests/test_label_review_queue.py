from __future__ import annotations

import csv

from scripts.export_label_review_queue import build_review_queue


def test_review_queue_exports_only_ambiguous_unlabelled_rows(tmp_path):
    source = tmp_path / "unlabelled.csv"
    output = tmp_path / "review.csv"
    rows = [
        {"repo": "org/healthy", "snapshot_at_utc": "2026-09-05T00:00:00+00:00", "language": "Python", "stars": "10", "size_kb": "100", "catalog_pushed_at": "x", "archived": "0", "latest_release_age_days": "50", "latest_release_at": "x"},
        {"repo": "org/boundary", "snapshot_at_utc": "2026-09-05T00:00:00+00:00", "language": "Go", "stars": "200", "size_kb": "100", "catalog_pushed_at": "x", "archived": "0", "latest_release_age_days": "165", "latest_release_at": "x"},
        {"repo": "org/missing", "snapshot_at_utc": "2026-09-05T00:00:00+00:00", "language": "Rust", "stars": "4000", "size_kb": "100", "catalog_pushed_at": "x", "archived": "0", "latest_release_age_days": "", "latest_release_at": ""},
        {"repo": "org/archived", "snapshot_at_utc": "2026-09-05T00:00:00+00:00", "language": "Python", "stars": "1", "size_kb": "100", "catalog_pushed_at": "x", "archived": "1", "latest_release_age_days": "", "latest_release_at": ""},
    ]
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = build_review_queue(source, output, limit=10)
    assert result == {"source_rows": 4, "review_candidates": 2, "exported_rows": 2}

    with output.open(encoding="utf-8", newline="") as handle:
        exported = list(csv.DictReader(handle))
    assert {row["repo"] for row in exported} == {"org/boundary", "org/missing"}
    assert {row["review_reason"] for row in exported} == {"ambiguous_release_boundary", "missing_release_evidence"}
    assert {row["language"] for row in exported} == {"Go", "Rust"}
    assert all(row["human_label"] == "" for row in exported)


def test_review_queue_round_robins_context_strata(tmp_path):
    source = tmp_path / "unlabelled.csv"
    output = tmp_path / "review.csv"
    rows = []
    for index in range(4):
        rows.append({
            "repo": f"python/repo-{index}",
            "snapshot_at_utc": "2026-09-05T00:00:00+00:00",
            "language": "Python",
            "stars": "5",
            "size_kb": "100",
            "catalog_pushed_at": "x",
            "archived": "0",
            "latest_release_age_days": "",
            "latest_release_at": "",
        })
    rows.append({
        "repo": "rust/unique",
        "snapshot_at_utc": "2026-09-05T00:00:00+00:00",
        "language": "Rust",
        "stars": "5000",
        "size_kb": "100",
        "catalog_pushed_at": "x",
        "archived": "0",
        "latest_release_age_days": "",
        "latest_release_at": "",
    })

    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    build_review_queue(source, output, limit=2)
    with output.open(encoding="utf-8", newline="") as handle:
        exported = list(csv.DictReader(handle))

    assert {row["language"] for row in exported} == {"Python", "Rust"}
