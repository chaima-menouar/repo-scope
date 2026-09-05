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
CHECKPOINT_EVERY = 1_000
STATE_SCHEME = 2


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _partitions() -> list[tuple[bool, str, str, int]]:
    """Interleave languages and popularity bands so each bounded run stays diverse."""
    active: list[tuple[bool, str, str, int]] = []
    archived: list[tuple[bool, str, str, int]] = []
    for year in reversed(YEARS):
        for stars in STAR_BUCKETS:
            for language in LANGUAGES:
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


def _load_state(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 1
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("scheme", 0)) != STATE_SCHEME:
            return 0, 1
        partition_index = max(0, int(payload.get("partition_index", 0)))
        page = max(1, min(10, int(payload.get("page", 1))))
        return partition_index, page
    except (ValueError, TypeError, json.JSONDecodeError):
        return 0, 1


def _write_checkpoint(
    *,
    rows: dict[str, dict[str, str]],
    output: Path,
    state_path: Path,
    partition_index: int,
    page: int,
    target: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(list(rows.values())[:target])
    temporary.replace(output)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {"scheme": STATE_SCHEME, "partition_index": partition_index, "page": page},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


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
    partition_index, start_page = _load_state(state_path)
    partition_index = min(partition_index, len(partitions))
    if len(rows) >= target:
        return {"total": len(rows), "added": 0, "partition_index": partition_index, "page": start_page}

    session = requests.Session()
    session.headers.update(_headers())
    added = 0
    last_checkpoint = 0

    while partition_index < len(partitions) and len(rows) < target and added < max_new:
        archived, language, stars, year = partitions[partition_index]
        query = (
            f"language:{language} stars:{stars} archived:{str(archived).lower()} "
            f"created:{year}-01-01..{year}-12-31"
        )
        page = start_page
        partition_finished = False
        while page <= 10 and len(rows) < target and added < max_new:
            items = _request(session, query, page)
            if not items:
                partition_finished = True
                break
            hit_batch_limit = False
            for item in items:
                record = _row(item)
                repo = str(record["repo"])
                if repo and repo not in rows:
                    rows[repo] = {key: str(value) for key, value in record.items()}
                    added += 1
                    if added - last_checkpoint >= CHECKPOINT_EVERY:
                        _write_checkpoint(
                            rows=rows,
                            output=output,
                            state_path=state_path,
                            partition_index=partition_index,
                            page=page,
                            target=target,
                        )
                        last_checkpoint = added
                        print(f"checkpoint: total={len(rows)} added={added}", flush=True)
                    if len(rows) >= target or added >= max_new:
                        hit_batch_limit = True
                        break
            if hit_batch_limit:
                _write_checkpoint(
                    rows=rows,
                    output=output,
                    state_path=state_path,
                    partition_index=partition_index,
                    page=page,
                    target=target,
                )
                return {
                    "total": min(len(rows), target),
                    "added": added,
                    "partition_index": partition_index,
                    "page": page,
                }
            if len(items) < 100:
                partition_finished = True
                break
            page += 1
            _write_checkpoint(
                rows=rows,
                output=output,
                state_path=state_path,
                partition_index=partition_index,
                page=page,
                target=target,
            )
            time.sleep(2.1)

        if partition_finished or page > 10:
            partition_index += 1
            start_page = 1
            _write_checkpoint(
                rows=rows,
                output=output,
                state_path=state_path,
                partition_index=partition_index,
                page=1,
                target=target,
            )
        else:
            start_page = page

    _write_checkpoint(
        rows=rows,
        output=output,
        state_path=state_path,
        partition_index=partition_index,
        page=start_page,
        target=target,
    )
    return {
        "total": min(len(rows), target),
        "added": added,
        "partition_index": partition_index,
        "page": start_page,
    }


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
        f"partition_index={result['partition_index']} page={result['page']} target={args.target}"
    )


if __name__ == "__main__":
    main()
