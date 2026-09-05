from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _count_csv(path: Path) -> tuple[int, int]:
    if not path.exists() or path.stat().st_size == 0:
        return 0, 0
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    repositories = {(row.get("repo") or "").strip() for row in rows if (row.get("repo") or "").strip()}
    return len(rows), len(repositories)


def validate(progress_path: Path, catalog_path: Path, deep_path: Path) -> dict[str, int]:
    previous: dict = {}
    if progress_path.exists() and progress_path.stat().st_size:
        previous = json.loads(progress_path.read_text(encoding="utf-8"))

    catalog_rows, catalog_unique = _count_csv(catalog_path)
    deep_rows, deep_unique = _count_csv(deep_path)
    previous_catalog = int(previous.get("catalog_repositories", 0) or 0)
    previous_deep = int(previous.get("deep_snapshots", 0) or 0)

    if catalog_rows < previous_catalog:
        raise ValueError(
            f"Catalog regressed from {previous_catalog} to {catalog_rows} rows; refusing to commit data loss."
        )
    if deep_rows < previous_deep:
        raise ValueError(
            f"Deep dataset regressed from {previous_deep} to {deep_rows} rows; refusing to commit data loss."
        )
    if deep_rows != deep_unique:
        raise ValueError(
            f"Deep dataset contains duplicate repository snapshots in a single-snapshot dataset: {deep_rows} rows, "
            f"{deep_unique} unique repositories."
        )
    if catalog_rows != catalog_unique:
        raise ValueError(
            f"Catalog contains duplicate repository rows: {catalog_rows} rows, {catalog_unique} unique repositories."
        )

    return {
        "previous_catalog": previous_catalog,
        "catalog_rows": catalog_rows,
        "previous_deep": previous_deep,
        "deep_rows": deep_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reject RepoScope dataset runs that lose accumulated rows.")
    parser.add_argument("--progress", default="data/repo_risk_100k_progress.json")
    parser.add_argument("--catalog", default="data/repository_catalog_100k.csv")
    parser.add_argument("--deep", default="data/repo_risk_unlabelled_100k.csv")
    args = parser.parse_args()
    result = validate(Path(args.progress), Path(args.catalog), Path(args.deep))
    print(result)


if __name__ == "__main__":
    main()
