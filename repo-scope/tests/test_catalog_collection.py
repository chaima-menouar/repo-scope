from __future__ import annotations

import json

from scripts import collect_repository_catalog as catalog


def test_catalog_caps_each_stratum_to_first_page_and_advances_state(tmp_path, monkeypatch):
    output = tmp_path / "catalog.csv"
    state = tmp_path / "state.json"
    partitions = [
        (False, "Python", "0..10", 2026),
        (False, "Go", "0..10", 2026),
    ]
    monkeypatch.setattr(catalog, "_partitions", lambda: partitions)
    calls = []

    def fake_request(session, query, page=1):
        calls.append((query, page))
        if "language:Python" in query:
            return [{"full_name": f"python/repo-{index}"} for index in range(100)]
        return [{"full_name": f"go/repo-{index}"} for index in range(100)]

    monkeypatch.setattr(catalog, "_request", fake_request)
    monkeypatch.setattr(catalog.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        catalog,
        "_row",
        lambda item: {key: (item["full_name"] if key == "repo" else "") for key in catalog.FIELDS},
    )

    result = catalog.collect(200, output, state, max_new=200)

    assert result["total"] == 200
    assert result["partition_index"] == 2
    assert result["page"] == 1
    assert len(calls) == 2
    assert all(page == 1 for _, page in calls)
    assert set(catalog._load_rows(output)) == {
        *(f"python/repo-{index}" for index in range(100)),
        *(f"go/repo-{index}" for index in range(100)),
    }
    assert json.loads(state.read_text(encoding="utf-8")) == {
        "scheme": catalog.STATE_SCHEME,
        "partition_index": 2,
        "page": 1,
    }


def test_catalog_resumes_at_next_stratum_without_duplicate_rows(tmp_path, monkeypatch):
    output = tmp_path / "catalog.csv"
    state = tmp_path / "state.json"
    partitions = [
        (False, "Python", "0..10", 2026),
        (False, "Go", "0..10", 2026),
    ]
    monkeypatch.setattr(catalog, "_partitions", lambda: partitions)
    monkeypatch.setattr(catalog.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        catalog,
        "_request",
        lambda session, query, page=1: (
            [{"full_name": "org/python"}] if "language:Python" in query else [{"full_name": "org/go"}]
        ),
    )
    monkeypatch.setattr(
        catalog,
        "_row",
        lambda item: {key: (item["full_name"] if key == "repo" else "") for key in catalog.FIELDS},
    )

    first = catalog.collect(10, output, state, max_new=1)
    second = catalog.collect(10, output, state, max_new=1)

    assert first["partition_index"] == 1
    assert second["partition_index"] == 2
    assert set(catalog._load_rows(output)) == {"org/python", "org/go"}


def test_legacy_catalog_state_resets_when_partition_scheme_changes(tmp_path):
    state = tmp_path / "state.json"
    state.write_text('{"scheme": 2, "partition_index": 7, "page": 3}\n', encoding="utf-8")
    assert catalog._load_state(state) == (0, 1)


def test_partition_prefix_interleaves_languages_and_archive_states():
    prefix = catalog._partitions()[:40]
    languages = {language for _, language, _, _ in prefix}
    archive_states = {archived for archived, _, _, _ in prefix}
    assert len(languages) >= 8
    assert archive_states == {False, True}
