from __future__ import annotations

import argparse
import csv
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
YEARS = list(range(2008, 2027))
FIELDS = [
    "repo", "language", "stars", "forks", "open_issues", "size_kb", "archived",
    "created_at", "updated_at", "pushed_at", "default_branch", "license", "topics",
]


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _partitions() -> list[tuple[bool, str, str, int]]:
    active: list[tuple[bool, str, str, int]] = []
    archived: list[tuple[bool, str, str, int]] = []
    for year in reversed(YEARS):
        for language in LANGUAGES:
            for stars in STAR_BUCKETS:
                active.append((False, language, stars, year))
                archived.append((True, language, stars, year))
    mixed: list[tuple[bool, str, str, int]] = []
    ai = ri = 0
    while ai < len(active) or ri < len(archived):
        for _ in range(4):
            if ai < len(active):
                mixed.append(active[ai])
                ai += 1
        if ri < len(archived):
            mixed.append(archived[ri])
            ri += 1
    return mixed


def _load_rows(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["repo"]: row for row in csv.DictReader(handle) if row.get("repo")}


def _load_state(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return max(0, int(json.loads(path.read_text(encoding="utf-8")).get("partition_index", 0)))
    except (ValueError, TypeError, json.JSONDecodeError):
        return 0


def _request(session: requests.Session, query: str, page: int) -> list[dict]:
    for attempt in range(6):
        response = session.get(
            API,
            params={"q": query, "sort": "updated", "order": "desc", "per_page": 100, "page": page},
            timeout=30,
        )
        if response.status_code in {403, 429}:
            reset = int(response.headers.get("X-RateLimit-Reset", "0") or 0)
            time.sleep(max(5, min(75, reset - int(time.time()) + 2)))
            continue
        if response.status_code >= 500 and attempt < 5:
            time.sleep(min(30, 2**attempt))
            continue
        response.raise_for_status()
        return response.json().get("items", [])
    return []


def _row(item: dict) -> dict[str, object]:
    license_info = item.get("license") or {}
    return {
        "repo": item.get("full_name") or "",
        "language": item.get("language") or "",
        "stars": item.get("stargazers_count") or 0,
        "forks": item.get("forks_count") or 0,
        "open_issues": item.get("open_issues_count") or 0,
        "size_kb": item.get("size") or 0,
        "archived": int(bool(item.get("archived"))),
        "created_at": item.get("created_at") or "",
        "updated_at": item.get("updated_at") or "",
        "pushed_at": item.get("pushed_at") or "",
        "default_branch": item.get("default_branch") or "",
        "license": license_info.get("spdx_id") or "",
        "topics": "|".join(item.get("topics") or []),
    }


def collect(target: int, output: Path, state_path: Path, max_new: int) -> dict[str, int]:
    rows = _load_rows(output)
    partitions = _partitions()
    partition_index = min(_load_state(state_path), len(partitions))
    if len(rows) >= target:
        return {"total": len(rows), "added": 0, "partition_index": partition_index}

    session = requests.Session()
    session.headers.update(_headers())
    added = 0
    while partition_index < len(partitions) and len(rows) < target and added < max_new:
        archived, language, stars, year = partitions[partition_index]
        query = (
            f"language:{language} stars:{stars} fork:false archived:{str(archived).lower()} "
            f"created:{year}-01-01..{year}-12-31"
        )
        for page in range(1, 11):
            items = _request(session, query, page)
            if not items:
                break
            for item in items:
                record = _row(item)
                repo = str(record["repo"])
                if repo and repo not in rows:
                    rows[repo] = {key: str(value) for key, value in record.items()}
                    added += 1
                    if len(rows) >= target or added >= max_new:
                        break
            if len(rows) >= target or added >= max_new or len(items) < 100:
                break
            time.sleep(2.1)
        partition_index += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(list(rows.values())[:target])
    state_path.write_text(json.dumps({"partition_index": partition_index}, indent=2) + "\n", encoding="utf-8")
    return {"total": min(len(rows), target), "added": added, "partition_index": partition_index}


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a scalable public GitHub repository catalog.")
    parser.add_argument("--target", type=int, default=100_000)
    parser.add_argument("--output", default="data/repository_catalog_100k.csv")
    parser.add_argument("--state", default="data/repository_catalog_100k.state.json")
    parser.add_argument("--max-new", type=int, default=100_000)
    args = parser.parse_args()
    result = collect(args.target, Path(args.output), Path(args.state), args.max_new)
    print(
        f"catalog: total={result['total']} added={result['added']} "
        f"partition_index={result['partition_index']} target={args.target}"
    )


if __name__ == "__main__":
    main()
