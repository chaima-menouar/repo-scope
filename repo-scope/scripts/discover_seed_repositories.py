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


def discover(target: int) -> list[str]:
    repos: dict[str, None] = {}
    session = requests.Session()
    session.headers.update(_headers())

    # Each query is capped by GitHub search at 1,000 accessible results, so we
    # deliberately partition by language and star range for broad coverage.
    for language in LANGUAGES:
        for stars in STAR_BUCKETS:
            query = f"language:{language} stars:{stars} fork:false archived:false"
            for page in range(1, 11):
                response = session.get(
                    API,
                    params={"q": query, "sort": "updated", "order": "desc", "per_page": 100, "page": page},
                    timeout=30,
                )
                if response.status_code == 403 and "rate limit" in response.text.lower():
                    reset = int(response.headers.get("X-RateLimit-Reset", "0") or 0)
                    sleep_for = max(5, min(70, reset - int(time.time()) + 2))
                    time.sleep(sleep_for)
                    continue
                response.raise_for_status()
                items = response.json().get("items", [])
                if not items:
                    break
                for item in items:
                    full_name = item.get("full_name")
                    if full_name:
                        repos.setdefault(full_name, None)
                        if len(repos) >= target:
                            return list(repos)
                if len(items) < 100:
                    break
                time.sleep(1.2)  # search API has a separate, tighter rate limit
    return list(repos)


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover a diverse public GitHub repository seed set.")
    parser.add_argument("--target", type=int, default=10_000)
    parser.add_argument("--output", default="data/seed_repositories_10k.txt")
    args = parser.parse_args()

    repos = discover(args.target)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(repos) + "\n", encoding="utf-8")
    print(f"wrote {len(repos)} unique repositories to {output}")
    if len(repos) < args.target:
        raise SystemExit(f"Only discovered {len(repos)} repositories; target was {args.target}.")


if __name__ == "__main__":
    main()
