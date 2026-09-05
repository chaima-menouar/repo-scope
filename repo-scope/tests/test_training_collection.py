from __future__ import annotations

import pytest

from scripts import collect_training_data as collector


def _row(repo: str) -> dict:
    return {
        "repo": repo,
        "days_since_last_commit": 1,
        "bus_factor": 2,
        "issue_closure_rate_pct": 80,
        "pr_merge_rate_pct": 70,
        "commits_90d": 20,
        "contributors_sampled": 5,
        "has_ci": 1,
        "has_tests": 1,
        "snapshot_at_utc": "2026-09-05T00:00:00+00:00",
        "archived": 0,
        "latest_release_age_days": 20,
        "latest_release_at": "2026-08-01T00:00:00Z",
        "language": "Python",
        "stars": 10,
        "forks": 1,
        "open_issues": 2,
        "size_kb": 100,
        "catalog_pushed_at": "2026-09-01T00:00:00Z",
        "label": "",
    }


def test_deep_collection_checkpoints_and_resumes_without_duplicates(tmp_path, monkeypatch):
    output = tmp_path / "deep.csv"
    repositories = ["org/a", "org/b", "org/c"]
    calls: list[str] = []

    def fake_collect(repo: str, catalog_row=None) -> dict:
        calls.append(repo)
        return _row(repo)

    monkeypatch.setattr(collector, "_collect_one", fake_collect)

    total, failures, previous = collector.collect(
        repositories,
        output,
        workers=1,
        resume=True,
        limit=2,
        checkpoint_every=1,
    )
    assert total == 2
    assert previous == 0
    assert failures == []
    assert set(calls) == {"org/a", "org/b"}

    calls.clear()
    total, failures, previous = collector.collect(
        repositories,
        output,
        workers=1,
        resume=True,
        limit=2,
        checkpoint_every=1,
    )
    assert total == 3
    assert previous == 2
    assert failures == []
    assert calls == ["org/c"]
    assert set(collector.load_existing(output)) == set(repositories)


def test_manifest_changes_never_drop_previously_collected_snapshots(tmp_path, monkeypatch):
    output = tmp_path / "deep.csv"

    def fake_collect(repo: str, catalog_row=None) -> dict:
        return _row(repo)

    monkeypatch.setattr(collector, "_collect_one", fake_collect)

    total, failures, _ = collector.collect(
        ["org/a", "org/b"],
        output,
        workers=1,
        resume=True,
        checkpoint_every=1,
    )
    assert total == 2
    assert failures == []

    total, failures, previous = collector.collect(
        ["org/b", "org/c"],
        output,
        workers=1,
        resume=True,
        checkpoint_every=1,
    )
    assert previous == 2
    assert total == 3
    assert failures == []
    assert set(collector.load_existing(output)) == {"org/a", "org/b", "org/c"}


def test_collection_passes_catalog_metadata_to_worker(tmp_path, monkeypatch):
    output = tmp_path / "deep.csv"
    seen = []

    def fake_collect(repo: str, catalog_row=None) -> dict:
        seen.append((repo, catalog_row))
        return _row(repo)

    monkeypatch.setattr(collector, "_collect_one", fake_collect)
    catalog_rows = {"org/a": {"repo": "org/a", "archived": "1", "default_branch": "main"}}

    total, failures, _ = collector.collect(
        ["org/a"],
        output,
        workers=1,
        catalog_rows=catalog_rows,
    )

    assert total == 1
    assert failures == []
    assert seen == [("org/a", catalog_rows["org/a"])]


def test_batch_outcome_rejects_zero_new_rows_when_requests_failed():
    with pytest.raises(RuntimeError, match="added 0 new snapshots"):
        collector.validate_batch_outcome(680, 680, [("org/a", "rate limited")])


def test_batch_outcome_allows_partial_progress_despite_some_failures():
    collector.validate_batch_outcome(681, 680, [("org/b", "transient failure")])
