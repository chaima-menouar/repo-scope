from __future__ import annotations

import argparse
import csv
from collections import defaultdict, deque
from pathlib import Path

from repo_scope.ml.labels import assign_weak_label

REVIEW_COLUMNS = [
    "repo",
    "snapshot_at_utc",
    "language",
    "stars",
    "size_kb",
    "catalog_pushed_at",
    "archived",
    "latest_release_age_days",
    "latest_release_at",
    "review_reason",
    "human_label",
    "review_notes",
]


def _reason(row: dict[str, str]) -> str:
    raw_age = (row.get("latest_release_age_days") or "").strip()
    if not raw_age:
        return "missing_release_evidence"
    try:
        age = int(float(raw_age))
    except ValueError:
        return "invalid_release_evidence"
    if 151 <= age <= 179:
        return "ambiguous_release_boundary"
    return "insufficient_independent_evidence"


def _star_bucket(value: str) -> str:
    try:
        stars = int(float(value or 0))
    except ValueError:
        return "unknown"
    if stars <= 25:
        return "0-25"
    if stars <= 100:
        return "26-100"
    if stars <= 500:
        return "101-500"
    if stars <= 2000:
        return "501-2000"
    return "2001+"


def _stratified_select(candidates: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    """Round-robin ambiguous cases across reason, language and popularity strata."""
    groups: dict[tuple[str, str, str], deque[dict[str, str]]] = defaultdict(deque)
    for row in sorted(candidates, key=lambda item: item["repo"]):
        key = (
            row["review_reason"],
            row.get("language") or "unknown",
            _star_bucket(row.get("stars") or ""),
        )
        groups[key].append(row)

    keys = sorted(groups)
    selected: list[dict[str, str]] = []
    while keys and len(selected) < max(0, limit):
        next_keys: list[tuple[str, str, str]] = []
        for key in keys:
            bucket = groups[key]
            if bucket and len(selected) < limit:
                selected.append(bucket.popleft())
            if bucket:
                next_keys.append(key)
        keys = next_keys
    return selected


def build_review_queue(source: Path, output: Path, limit: int = 250) -> dict[str, int]:
    if not source.exists() or source.stat().st_size == 0:
        raise ValueError(f"Source dataset does not exist or is empty: {source}")

    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        repo = (row.get("repo") or "").strip()
        if not repo or repo in seen or assign_weak_label(row) is not None:
            continue
        seen.add(repo)
        candidates.append(
            {
                "repo": repo,
                "snapshot_at_utc": row.get("snapshot_at_utc", ""),
                "language": row.get("language", ""),
                "stars": row.get("stars", ""),
                "size_kb": row.get("size_kb", ""),
                "catalog_pushed_at": row.get("catalog_pushed_at", ""),
                "archived": row.get("archived", ""),
                "latest_release_age_days": row.get("latest_release_age_days", ""),
                "latest_release_at": row.get("latest_release_at", ""),
                "review_reason": _reason(row),
                "human_label": "",
                "review_notes": "",
            }
        )

    selected = _stratified_select(candidates, limit)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(selected)

    return {
        "source_rows": len(rows),
        "review_candidates": len(candidates),
        "exported_rows": len(selected),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a stratified ambiguous RepoScope queue for human label review.")
    parser.add_argument("--input", default="data/repo_risk_unlabelled_100k.csv")
    parser.add_argument("--output", default="data/repo_risk_human_review_queue.csv")
    parser.add_argument("--limit", type=int, default=250)
    args = parser.parse_args()
    result = build_review_queue(Path(args.input), Path(args.output), args.limit)
    print(result)


if __name__ == "__main__":
    main()
