from __future__ import annotations

import argparse
import csv
from collections import defaultdict, deque
from datetime import datetime, timezone
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


def _is_stale_active(row: dict[str, str], stale_after_days: int = 365) -> bool:
    """Sampling proxy only; this value is never used as a training label."""
    raw = (row.get("pushed_at") or "").strip()
    if not raw:
        return True
    try:
        pushed = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return True
    return (datetime.now(timezone.utc) - pushed).days >= stale_after_days


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


def _interleave(primary: list[str], secondary: list[str], secondary_fraction: float) -> list[str]:
    """Spread the secondary pool through the output instead of appending it."""
    primary_queue = deque(primary)
    secondary_queue = deque(secondary)
    selected: list[str] = []
    secondary_used = 0
    total = len(primary) + len(secondary)

    for position in range(total):
        desired_secondary = round((position + 1) * secondary_fraction)
        choose_secondary = secondary_queue and secondary_used < desired_secondary
        if choose_secondary:
            selected.append(secondary_queue.popleft())
            secondary_used += 1
        elif primary_queue:
            selected.append(primary_queue.popleft())
        elif secondary_queue:
            selected.append(secondary_queue.popleft())
            secondary_used += 1
    return selected


def build_manifest(
    catalog: Path,
    output: Path,
    target: int = 10_000,
    archived_fraction: float = 0.20,
    stale_active_fraction: float = 0.35,
    stale_after_days: int = 365,
) -> dict[str, int]:
    if not catalog.exists() or catalog.stat().st_size == 0:
        raise ValueError(f"Catalog does not exist or is empty: {catalog}")
    with catalog.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    archived_target = min(target, round(target * archived_fraction))
    active_target = max(0, target - archived_target)
    active_rows = [row for row in rows if not _is_archived(row)]
    archived_rows = [row for row in rows if _is_archived(row)]

    stale_active_rows = [row for row in active_rows if _is_stale_active(row, stale_after_days)]
    recent_active_rows = [row for row in active_rows if not _is_stale_active(row, stale_after_days)]
    stale_active_target = round(active_target * stale_active_fraction)
    recent_active_target = active_target - stale_active_target

    recent_active = _round_robin(recent_active_rows, recent_active_target)
    stale_active = _round_robin(stale_active_rows, stale_active_target)
    active = _interleave(recent_active, stale_active, stale_active_fraction)

    active_set = set(active)
    if len(active) < min(active_target, len(active_rows)):
        remainder_active = [repo for repo in _round_robin(active_rows, active_target) if repo not in active_set]
        active.extend(remainder_active[: active_target - len(active)])

    archived = _round_robin(archived_rows, archived_target)
    selected = _interleave(active, archived, archived_fraction)

    selected_set = set(selected)
    if len(selected) < min(target, len(rows)):
        remainder = [repo for repo in _round_robin(rows, target) if repo not in selected_set]
        selected.extend(remainder[: target - len(selected)])

    archived_repos = {(row.get("repo") or "").strip() for row in rows if _is_archived(row)}
    stale_active_repos = {
        (row.get("repo") or "").strip()
        for row in active_rows
        if _is_stale_active(row, stale_after_days)
    }
    archived_count = sum(1 for repo in selected if repo in archived_repos)
    stale_active_count = sum(1 for repo in selected if repo in stale_active_repos)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")
    return {
        "catalog_rows": len(rows),
        "manifest_rows": len(selected),
        "active_selected": len(selected) - archived_count,
        "archived_selected": archived_count,
        "stale_active_selected": stale_active_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a diverse RepoScope deep-analysis manifest.")
    parser.add_argument("--catalog", default="data/repository_catalog_100k.csv")
    parser.add_argument("--output", default="data/seed_repositories_100k.txt")
    parser.add_argument("--target", type=int, default=10_000)
    parser.add_argument("--archived-fraction", type=float, default=0.20)
    parser.add_argument("--stale-active-fraction", type=float, default=0.35)
    parser.add_argument("--stale-after-days", type=int, default=365)
    args = parser.parse_args()
    if not 0 <= args.archived_fraction <= 1:
        raise SystemExit("--archived-fraction must be between 0 and 1")
    if not 0 <= args.stale_active_fraction <= 1:
        raise SystemExit("--stale-active-fraction must be between 0 and 1")
    if args.stale_after_days < 1:
        raise SystemExit("--stale-after-days must be positive")
    result = build_manifest(
        Path(args.catalog),
        Path(args.output),
        args.target,
        args.archived_fraction,
        args.stale_active_fraction,
        args.stale_after_days,
    )
    print(result)


if __name__ == "__main__":
    main()
