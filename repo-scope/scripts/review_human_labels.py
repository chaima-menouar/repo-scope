from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_LABELS = {"healthy", "watch", "risky"}
DECISION_COLUMNS = ["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"]

# Intentionally excludes review_reason, weak labels, model predictions, confidence,
# health scores and feature importance so reviewers remain blind to automation.
VISIBLE_EVIDENCE_COLUMNS = [
    "repo",
    "snapshot_at_utc",
    "language",
    "stars",
    "size_kb",
    "catalog_pushed_at",
    "archived",
    "latest_release_age_days",
    "latest_release_at",
]


def load_queue(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Review queue not found: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if (row.get("repo") or "").strip()]


def load_decisions(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if (row.get("repo") or "").strip()]


def load_assignments(path: Path, reviewer: str) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Review assignments not found: {path}")
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("Reviewer is required to load assignments.")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assigned = {
        (row.get("repo") or "").strip()
        for row in rows
        if (row.get("reviewer") or "").strip() == reviewer and (row.get("repo") or "").strip()
    }
    if not assigned:
        raise ValueError(
            f"Reviewer {reviewer} has no repositories in {path}. "
            "Refusing to fall back to the unassigned review queue."
        )
    return assigned


def visible_evidence(row: dict[str, str]) -> dict[str, str]:
    return {key: (row.get(key) or "").strip() for key in VISIBLE_EVIDENCE_COLUMNS}


def pending_reviews(
    queue: list[dict[str, str]],
    decisions: list[dict[str, str]],
    reviewer: str,
    assigned_repos: set[str] | None = None,
) -> list[dict[str, str]]:
    reviewer = reviewer.strip()
    reviewed_by_this_reviewer = {
        (row.get("repo") or "").strip()
        for row in decisions
        if (row.get("reviewer") or "").strip() == reviewer
    }
    return [
        row
        for row in queue
        if (row.get("repo") or "").strip()
        and (assigned_repos is None or (row.get("repo") or "").strip() in assigned_repos)
        and (row.get("repo") or "").strip() not in reviewed_by_this_reviewer
    ]


def save_review(
    decisions_path: Path,
    repo: str,
    label: str,
    notes: str,
    reviewer: str,
    *,
    reviewed_at_utc: str | None = None,
    replace: bool = False,
) -> dict[str, str]:
    repo = repo.strip()
    label = label.strip().lower()
    notes = notes.strip()
    reviewer = reviewer.strip()

    if not repo:
        raise ValueError("Repository is required.")
    if label not in ALLOWED_LABELS:
        raise ValueError(f"Label must be one of: {', '.join(sorted(ALLOWED_LABELS))}.")
    if not reviewer:
        raise ValueError("Reviewer is required for provenance.")
    if not notes:
        raise ValueError("Evidence-based review notes are required.")

    rows = load_decisions(decisions_path)
    existing_index = next(
        (
            index
            for index, row in enumerate(rows)
            if (row.get("repo") or "").strip() == repo
            and (row.get("reviewer") or "").strip() == reviewer
        ),
        None,
    )
    if existing_index is not None and not replace:
        raise ValueError(
            f"{repo} already has a decision from reviewer {reviewer}. "
            "Use replace=True only for a deliberate correction."
        )

    timestamp = reviewed_at_utc or datetime.now(timezone.utc).isoformat()
    review = {
        "repo": repo,
        "human_label": label,
        "review_notes": notes,
        "reviewer": reviewer,
        "reviewed_at_utc": timestamp,
    }

    if existing_index is None:
        rows.append(review)
    else:
        rows[existing_index] = review

    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    with decisions_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DECISION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return review


def _print_candidate(row: dict[str, str], index: int, total: int) -> None:
    evidence = visible_evidence(row)
    print(f"\n[{index}/{total}] {evidence['repo']}")
    print(f"GitHub: https://github.com/{evidence['repo']}")
    for key in VISIBLE_EVIDENCE_COLUMNS[1:]:
        value = evidence[key] or "unknown"
        print(f"{key}: {value}")
    print("\nInspect the public repository using docs/HUMAN_LABEL_RUBRIC.md before assigning a label.")


def interactive_review(
    queue_path: Path,
    decisions_path: Path,
    reviewer: str,
    limit: int | None = None,
    assignments_path: Path | None = None,
) -> dict[str, int]:
    queue = load_queue(queue_path)
    decisions = load_decisions(decisions_path)
    assigned_repos = load_assignments(assignments_path, reviewer) if assignments_path else None
    pending = pending_reviews(queue, decisions, reviewer, assigned_repos)
    if limit is not None:
        pending = pending[: max(0, limit)]

    saved = 0
    skipped = 0
    for index, row in enumerate(pending, start=1):
        _print_candidate(row, index, len(pending))
        while True:
            choice = input("Label [healthy/watch/risky/skip/quit]: ").strip().lower()
            if choice == "quit":
                return {"saved": saved, "skipped": skipped, "remaining": len(pending) - index + 1}
            if choice == "skip":
                skipped += 1
                break
            if choice not in ALLOWED_LABELS:
                print("Invalid choice. Use healthy, watch, risky, skip, or quit.")
                continue
            notes = input("Evidence-based review notes: ").strip()
            if not notes:
                print("Notes are required; describe the evidence behind the judgement.")
                continue
            save_review(decisions_path, row["repo"], choice, notes, reviewer)
            saved += 1
            break

    return {"saved": saved, "skipped": skipped, "remaining": 0}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Blind independent human review CLI for RepoScope maintenance-risk validation."
    )
    parser.add_argument("--queue", default="data/repo_risk_human_review_queue.csv")
    parser.add_argument(
        "--decisions",
        default="data/repo_risk_human_review_decisions.csv",
        help="Append-only-by-reviewer decision registry. Multiple reviewers may review the same repository independently.",
    )
    parser.add_argument(
        "--assignments",
        default=None,
        help="Optional blind reviewer/repository assignment CSV generated by build_human_review_assignments.py.",
    )
    parser.add_argument("--reviewer", required=True, help="Stable reviewer identifier stored for provenance.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum pending candidates to review in this session.")
    args = parser.parse_args()

    result = interactive_review(
        Path(args.queue),
        Path(args.decisions),
        args.reviewer,
        args.limit,
        Path(args.assignments) if args.assignments else None,
    )
    print(f"\nReview session complete: {result}")


if __name__ == "__main__":
    main()
