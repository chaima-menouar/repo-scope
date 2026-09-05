from __future__ import annotations

import argparse
import csv
from collections import defaultdict, deque
from pathlib import Path


def _star_bucket(raw: str) -> str:
    try:
        stars = int(float(raw or 0))
    except ValueError:
        stars = 0
    if stars <= 10:
        return "0-10"
    if stars <= 50:
        return "11-50"
    if stars <= 200:
        return "51-200"
    if stars <= 1000:
        return "201-1000"
    if stars <= 5000:
        return "1001-5000"
    return "5001+"


def _is_archived(row: dict[str, str]) -> bool:
    return (row.get("archived") or "").strip().lower() in {"1", "true", "yes"}


def _round_robin(rows: list[dict[str, str]], target: int) -> list[str]:
    strata: dict[tuple[str, str], deque[str]] = defaultdict(deque)
    for row in sorted(rows, key=lambda item: (item.get("language", ""), item.get("repo", ""))):
        repo = (row.get("repo") or "").strip()
        if not repo:
            continue
        language = (row.get("language") or "unknown").strip() or "unknown"
        strata[(language, _star_bucket(row.get("stars", "")))].append(repo)

    selected: list[str] = []
    keys = sorted(strata)
    while keys and len(selected) < target:
        next_keys: list[tuple[str, str]] = []
        for key in keys:
            queue = strata[key]
            if queue and len(selected) < target:
                selected.append(queue.popleft())
            if queue:
                next_keys.append(key)
        keys = next_keys
    return selected


def _interleave(active: list[str], archived: list[str], archived_fraction: float) -> list[str]:
    """Spread archived examples across the manifest instead of appending them at the end."""
    active_queue = deque(active)
    archived_queue = deque(archived)
    selected: list[str] = []
    archived_used = 0
    total = len(active) + len(archived)

    for position in range(total):
        desired_archived = round((position + 1) * archived_fraction)
        choose_archived = archived_queue and archived_used < desired_archived
        if choose_archived:
            selected.append(archived_queue.popleft())
            archived_used += 1
        elif active_queue:
            selected.append(active_queue.popleft())
        elif archived_queue:
            selected.append(archived_queue.popleft())
            archived_used += 1
    return selected


def build_manifest(catalog: Path, output: Path, target: int = 10_000, archived_fraction: float = 0.20) -> dict[str, int]:
    if not catalog.exists() or catalog.stat().st_size == 0:
        raise ValueError(f"Catalog does not exist or is empty: {catalog}")
    with catalog.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    archived_target = min(target, round(target * archived_fraction))
    active_target = max(0, target - archived_target)
    active_rows = [row for row in rows if not _is_archived(row)]
    archived_rows = [row for row in rows if _is_archived(row)]

    active = _round_robin(active_rows, active_target)
    archived = _round_robin(archived_rows, archived_target)
    selected = _interleave(active, archived, archived_fraction)

    selected_set = set(selected)
    if len(selected) < min(target, len(rows)):
        remainder = [repo for repo in _round_robin(rows, target) if repo not in selected_set]
        selected.extend(remainder[: target - len(selected)])

    archived_repos = {(row.get("repo") or "").strip() for row in rows if _is_archived(row)}
    archived_count = sum(1 for repo in selected if repo in archived_repos)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")
    return {
        "catalog_rows": len(rows),
        "manifest_rows": len(selected),
        "active_selected": len(selected) - archived_count,
        "archived_selected": archived_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a diverse RepoScope deep-analysis manifest.")
    parser.add_argument("--catalog", default="data/repository_catalog_100k.csv")
    parser.add_argument("--output", default="data/seed_repositories_100k.txt")
    parser.add_argument("--target", type=int, default=10_000)
    parser.add_argument("--archived-fraction", type=float, default=0.20)
    args = parser.parse_args()
    if not 0 <= args.archived_fraction <= 1:
        raise SystemExit("--archived-fraction must be between 0 and 1")
    result = build_manifest(Path(args.catalog), Path(args.output), args.target, args.archived_fraction)
    print(result)


if __name__ == "__main__":
    main()
