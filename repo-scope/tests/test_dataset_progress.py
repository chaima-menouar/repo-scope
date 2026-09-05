from __future__ import annotations

import csv
import json

import pytest

from scripts.validate_dataset_progress import validate


def _write_csv(path, repos):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repo"])
        writer.writeheader()
        for repo in repos:
            writer.writerow({"repo": repo})


def test_progress_guard_accepts_growth(tmp_path):
    progress = tmp_path / "progress.json"
    catalog = tmp_path / "catalog.csv"
    deep = tmp_path / "deep.csv"
    progress.write_text(json.dumps({"catalog_repositories": 2, "deep_snapshots": 1}), encoding="utf-8")
    _write_csv(catalog, ["org/a", "org/b", "org/c"])
    _write_csv(deep, ["org/a", "org/b"])

    result = validate(progress, catalog, deep)

    assert result["catalog_rows"] == 3
    assert result["deep_rows"] == 2


def test_progress_guard_rejects_deep_row_loss(tmp_path):
    progress = tmp_path / "progress.json"
    catalog = tmp_path / "catalog.csv"
    deep = tmp_path / "deep.csv"
    progress.write_text(json.dumps({"catalog_repositories": 2, "deep_snapshots": 3}), encoding="utf-8")
    _write_csv(catalog, ["org/a", "org/b"])
    _write_csv(deep, ["org/a", "org/b"])

    with pytest.raises(ValueError, match="Deep dataset regressed"):
        validate(progress, catalog, deep)


def test_progress_guard_rejects_duplicate_repositories(tmp_path):
    progress = tmp_path / "progress.json"
    catalog = tmp_path / "catalog.csv"
    deep = tmp_path / "deep.csv"
    progress.write_text("{}", encoding="utf-8")
    _write_csv(catalog, ["org/a", "org/b"])
    _write_csv(deep, ["org/a", "org/a"])

    with pytest.raises(ValueError, match="duplicate repository snapshots"):
        validate(progress, catalog, deep)
