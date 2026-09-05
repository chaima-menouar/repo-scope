from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests

API = "https://api.github.com/search/repositories"
LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#",
    "PHP", "Ruby", "Kotlin", "Swift", "Dart", "Shell", "Scala", "R",
]
STAR_BUCKETS = ["0..10", "11..50", "51..200", "201..1000", "1001..5000", ">5000"]
CREATED_YEARS = list(range(2008, 2027))


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _partitions(archived_fraction: float) -> list[tuple[bool, str, str, int]]:
    active: list[tuple[bool, str, str, int]] = []
    archived: list[tuple[bool, str, str, int]] = []
    for year in reversed(CREATED_YEARS):
        for language in LANGUAGES:
            for stars in STAR_BUCKETS:
                active.append((False, language, stars, year))
                archived.append((True, language, stars, year))

    # Interleave archived partitions instead of collecting them only at the end,
    # keeping the manifest diverse while it grows toward the final target.
    if archived_fraction <= 0:
        return active
    ratio = max(1, round((1 - archived_fraction) / archived_fraction))
    mixed: list[tuple[bool, str, str, int]] = []
    ai = ri = 0
    while ai < len(active) or ri < len(archived):
        for _ in range(ratio):
            if ai < len(active):
                mixed.append(active[ai])
                ai += 1
        if ri < len(archived):
            mixed.append(archived[ri])
            ri += 1
    return mixed


def _load_manifest(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_state(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"partition_index": 0}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {"partition_index": max(0, int(payload.get("partition_index", 0)))}
    except (ValueError, TypeError, json.JSONDecodeError):
        return {"partition_index": 0}


def _request_page(session: requests.Session, query: str, page: int) -> list[dict]:
    for attempt in range(4):
        response = session.get(
            API,
            params={"q": query, "sort": "updated", "order": "desc", "per_page": 100, "page": page},
            timeout=30,
        )
        if response.status_code in {403, 429}:
            reset = int(response.headers.get("X-RateLimit-Reset", "0") or 0)
            sleep_for = max(5, min(70, reset - int(time.time()) + 2))
            time.sleep(sleep_for)
            continue
        if response.status_code >= 500 and attempt < 3:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        return response.json().get("items", [])
    return []


def discover_incremental(
    *,
    target: int,
    archived_fraction: float,
    output: Path,
    state_path: Path,
    max_new: int,
) -> dict[str, int]:
    repositories = _load_manifest(output)
    seen = set(repositories)
    if len(repositories) >= target:
        return {"total": len(repositories), "added": 0, "partition_index": _load_state(state_path)["partition_index"]}

    partitions = _partitions(archived_fraction)
    state = _load_state(state_path)
    partition_index = min(state["partition_index"], len(partitions))
    session = requests.Session()
    session.headers.update(_headers())
    added = 0

    while partition_index < len(partitions) and len(repositories) < target and added < max_new:
        archived, language, stars, year = partitions[partition_index]
        query = (
            f"language:{language} stars:{stars} fork:false "
            f"archived:{str(archived).lower()} created:{year}-01-01..{year}-12-31"
        )
        for page in range(1, 11):
            items = _request_page(session, query, page)
            if not items:
                break
            for item in items:
                full_name = item.get("full_name")
                if full_name and full_name not in seen:
                    seen.add(full_name)
                    repositories.append(full_name)
                    added += 1
                    if len(repositories) >= target or added >= max_new:
                        break
            if len(repositories) >= target or added >= max_new or len(items) < 100:
                break
            time.sleep(1.2)
        partition_index += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(repositories[:target]) + "\n", encoding="utf-8")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"partition_index": partition_index}, indent=2) + "\n", encoding="utf-8")
    return {"total": min(len(repositories), target), "added": added, "partition_index": partition_index}


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally discover a diverse public GitHub repository seed set.")
    parser.add_argument("--target", type=int, default=100_000)
    parser.add_argument("--archived-fraction", type=float, default=0.20)
    parser.add_argument("--output", default="data/seed_repositories_100k.txt")
    parser.add_argument("--state", default="data/seed_repositories_100k.state.json")
    parser.add_argument("--max-new", type=int, default=5_000)
    args = parser.parse_args()

    if not 0 <= args.archived_fraction < 1:
        raise SystemExit("--archived-fraction must be between 0 (inclusive) and 1 (exclusive).")
    if args.target < 1 or args.max_new < 1:
        raise SystemExit("--target and --max-new must be positive integers.")

    result = discover_incremental(
        target=args.target,
        archived_fraction=args.archived_fraction,
        output=Path(args.output),
        state_path=Path(args.state),
        max_new=args.max_new,
    )
    print(
        f"repository discovery: total={result['total']} added={result['added']} "
        f"partition_index={result['partition_index']} target={args.target}"
    )


if __name__ == "__main__":
    main()
