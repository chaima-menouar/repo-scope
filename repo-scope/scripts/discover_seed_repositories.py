from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import requests

API = "https://api.github.com/search/repositories"
LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#",
    "PHP", "Ruby", "Kotlin", "Swift", "Dart", "Shell", "Scala", "R",
]
STAR_BUCKETS = ["0..25", "26..100", "101..500", "501..2000", ">2000"]


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _discover_partition(session: requests.Session, *, archived: bool, target: int, seen: set[str]) -> list[str]:
    found: list[str] = []
    for language in LANGUAGES:
        for stars in STAR_BUCKETS:
            query = f"language:{language} stars:{stars} fork:false archived:{str(archived).lower()}"
            for page in range(1, 11):
                response = session.get(
                    API,
                    params={"q": query, "sort": "updated", "order": "desc", "per_page": 100, "page": page},
                    timeout=30,
                )
                if response.status_code == 403 and "rate limit" in response.text.lower():
                    reset = int(response.headers.get("X-RateLimit-Reset", "0") or 0)
                    time.sleep(max(5, min(70, reset - int(time.time()) + 2)))
                    continue
                response.raise_for_status()
                items = response.json().get("items", [])
                if not items:
                    break
                for item in items:
                    full_name = item.get("full_name")
                    if full_name and full_name not in seen:
                        seen.add(full_name)
                        found.append(full_name)
                        if len(found) >= target:
                            return found
                if len(items) < 100:
                    break
                time.sleep(1.2)
    return found


def discover(target: int, archived_fraction: float = 0.20) -> list[str]:
    session = requests.Session()
    session.headers.update(_headers())
    seen: set[str] = set()

    archived_target = max(1, round(target * archived_fraction))
    active_target = target - archived_target
    active = _discover_partition(session, archived=False, target=active_target, seen=seen)
    archived = _discover_partition(session, archived=True, target=archived_target, seen=seen)
    return active + archived


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover a diverse public GitHub repository seed set.")
    parser.add_argument("--target", type=int, default=10_000)
    parser.add_argument("--archived-fraction", type=float, default=0.20)
    parser.add_argument("--output", default="data/seed_repositories_10k.txt")
    args = parser.parse_args()

    if not 0 < args.archived_fraction < 1:
        raise SystemExit("--archived-fraction must be between 0 and 1.")

    repos = discover(args.target, args.archived_fraction)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(repos) + "\n", encoding="utf-8")
    print(f"wrote {len(repos)} unique repositories to {output}")
    if len(repos) < args.target:
        raise SystemExit(f"Only discovered {len(repos)} repositories; target was {args.target}.")


if __name__ == "__main__":
    main()
