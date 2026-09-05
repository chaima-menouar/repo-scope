from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

ASSIGNMENT_COLUMNS = ["reviewer", "repo"]


def load_queue(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Review queue not found: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if (row.get("repo") or "").strip()]


def _balanced_repo_order(rows: list[dict[str, str]]) -> list[str]:
    by_language: dict[str, list[str]] = defaultdict(list)
    seen_repos: set[str] = set()
    for row in rows:
        repo = (row.get("repo") or "").strip()
        if not repo or repo in seen_repos:
            continue
        seen_repos.add(repo)
        language = (row.get("language") or "unknown").strip() or "unknown"
        by_language[language].append(repo)

    for repos in by_language.values():
        repos.sort(key=str.lower)

    languages = sorted(by_language, key=str.lower)
    ordered: list[str] = []
    while True:
        added = False
        for language in languages:
            repos = by_language[language]
            if repos:
                ordered.append(repos.pop(0))
                added = True
        if not added:
            break
    return ordered


def build_assignments(
    rows: list[dict[str, str]],
    reviewers: list[str],
    *,
    per_reviewer: int,
    overlap: int,
) -> list[dict[str, str]]:
    reviewers = [reviewer.strip() for reviewer in reviewers if reviewer.strip()]
    if len(reviewers) < 2:
        raise ValueError("At least two reviewers are required for independent validation.")
    if len(set(reviewers)) != len(reviewers):
        raise ValueError("Reviewer identifiers must be unique.")
    if per_reviewer <= 0:
        raise ValueError("per_reviewer must be positive.")
    if overlap < 0:
        raise ValueError("overlap cannot be negative.")
    if overlap > per_reviewer:
        raise ValueError("overlap cannot exceed per_reviewer.")

    repos = _balanced_repo_order(rows)
    if per_reviewer > len(repos):
        raise ValueError("Review queue is too small for the requested per-reviewer assignment size.")

    overlap = min(overlap, len(repos))
    shared = repos[:overlap]
    remaining = repos[overlap:]
    private_needed = per_reviewer - overlap

    if len(remaining) < private_needed * len(reviewers):
        raise ValueError(
            "Review queue is too small for the requested disjoint reviewer assignments after shared overlap."
        )

    assignments: list[dict[str, str]] = []
    cursor = 0
    for reviewer in reviewers:
        assigned = list(shared)
        assigned.extend(remaining[cursor : cursor + private_needed])
        cursor += private_needed
        assignments.extend({"reviewer": reviewer, "repo": repo} for repo in assigned)
    return assignments


def write_assignments(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ASSIGNMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build blind RepoScope human-review assignments.")
    parser.add_argument("--queue", default="data/repo_risk_human_review_queue.csv")
    parser.add_argument("--output", default="data/repo_risk_human_review_assignments.csv")
    parser.add_argument("--reviewers", nargs="+", required=True)
    parser.add_argument("--per-reviewer", type=int, default=100)
    parser.add_argument("--overlap", type=int, default=60)
    args = parser.parse_args()

    assignments = build_assignments(
        load_queue(Path(args.queue)),
        args.reviewers,
        per_reviewer=args.per_reviewer,
        overlap=args.overlap,
    )
    write_assignments(Path(args.output), assignments)
    print(
        {
            "reviewers": len(set(row["reviewer"] for row in assignments)),
            "assignment_rows": len(assignments),
            "unique_repositories_assigned": len(set(row["repo"] for row in assignments)),
            "per_reviewer": args.per_reviewer,
            "shared_overlap": args.overlap,
        }
    )


if __name__ == "__main__":
    main()
