from __future__ import annotations

from collections import Counter, defaultdict

import pytest

from scripts.build_human_review_assignments import build_assignments


def _row(repo: str, language: str) -> dict[str, str]:
    return {"repo": repo, "language": language, "review_reason": "must_not_leak"}


def test_assignment_planner_creates_exact_shared_overlap():
    rows = [_row(f"org/repo-{index:03d}", "Python" if index % 2 else "Java") for index in range(180)]

    assignments = build_assignments(
        rows,
        ["reviewer-a", "reviewer-b"],
        per_reviewer=100,
        overlap=60,
    )

    by_reviewer: dict[str, set[str]] = defaultdict(set)
    for row in assignments:
        by_reviewer[row["reviewer"]].add(row["repo"])

    assert len(by_reviewer["reviewer-a"]) == 100
    assert len(by_reviewer["reviewer-b"]) == 100
    assert len(by_reviewer["reviewer-a"] & by_reviewer["reviewer-b"]) == 60
    assert set(assignments[0]) == {"reviewer", "repo"}


def test_assignment_planner_balances_language_order_before_private_split():
    rows = [
        _row("org/python-a", "Python"),
        _row("org/python-b", "Python"),
        _row("org/java-a", "Java"),
        _row("org/java-b", "Java"),
        _row("org/go-a", "Go"),
        _row("org/go-b", "Go"),
    ]

    assignments = build_assignments(
        rows,
        ["reviewer-a", "reviewer-b"],
        per_reviewer=2,
        overlap=1,
    )

    counts = Counter(row["reviewer"] for row in assignments)
    assert counts == {"reviewer-a": 2, "reviewer-b": 2}


def test_assignment_planner_rejects_duplicate_reviewer_ids():
    with pytest.raises(ValueError, match="unique"):
        build_assignments([_row("org/a", "Python")], ["reviewer-a", "reviewer-a"], per_reviewer=1, overlap=1)


def test_assignment_planner_rejects_impossible_capacity():
    rows = [_row(f"org/repo-{index}", "Python") for index in range(10)]

    with pytest.raises(ValueError, match="too small"):
        build_assignments(rows, ["reviewer-a", "reviewer-b"], per_reviewer=8, overlap=2)
