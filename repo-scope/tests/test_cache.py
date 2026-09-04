import repo_scope.fetch.cache as cache


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.write("owner/repo/test", {"ok": True}, ttl_seconds=60)
    assert cache.read("owner/repo/test") == {"ok": True}


def test_cache_expiry(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.write("expired", {"ok": True}, ttl_seconds=1)
    path = cache._path_for("expired")
    text = path.read_text()
    import json
    payload = json.loads(text)
    payload["expires_at"] = 0
    path.write_text(json.dumps(payload))
    assert cache.read("expired") is None
