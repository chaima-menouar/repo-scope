from __future__ import annotations

import json

from scripts import collect_repository_catalog as catalog


def test_catalog_resumes_same_page_without_skipping_items(tmp_path, monkeypatch):
    output = tmp_path / "catalog.csv"
    state = tmp_path / "state.json"
    monkeypatch.setattr(catalog, "_partitions", lambda: [(False, "Python", "0..10", 2026)])
    monkeypatch.setattr(
        catalog,
        "_request",
        lambda session, query, page: [
            {"full_name": "org/a"},
            {"full_name": "org/b"},
            {"full_name": "org/c"},
        ] if page == 1 else [],
    )
    monkeypatch.setattr(
        catalog,
        "_row",
        lambda item: {key: (item["full_name"] if key == "repo" else "") for key in catalog.FIELDS},
    )

    first = catalog.collect(10, output, state, max_new=2)
    assert first["total"] == 2
    assert first["partition_index"] == 0
    assert first["page"] == 1
    assert json.loads(state.read_text(encoding="utf-8")) == {
        "scheme": catalog.STATE_SCHEME,
        "partition_index": 0,
        "page": 1,
    }

    second = catalog.collect(10, output, state, max_new=2)
    assert second["total"] == 3
    assert second["partition_index"] == 1
    assert set(catalog._load_rows(output)) == {"org/a", "org/b", "org/c"}


def test_legacy_catalog_state_resets_when_partition_scheme_changes(tmp_path):
    state = tmp_path / "state.json"
    state.write_text('{"partition_index": 7, "page": 3}\n', encoding="utf-8")
    assert catalog._load_state(state) == (0, 1)


def test_partition_prefix_interleaves_languages_and_archive_states():
    prefix = catalog._partitions()[:40]
    languages = {language for _, language, _, _ in prefix}
    archive_states = {archived for archived, _, _, _ in prefix}
    assert len(languages) >= 8
    assert archive_states == {False, True}
