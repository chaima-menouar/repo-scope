"""Small JSON cache used to reduce GitHub API calls.

The cache intentionally stays simple: each key is stored as a single JSON file with
an expiry timestamp. On serverless hosts such as Vercel it automatically uses /tmp,
so the app remains writable while still benefiting from warm-instance caching.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from repo_scope.config import CACHE_DIR, CACHE_TTL_SECONDS


def _path_for(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{digest}.json"


def read(key: str) -> Any | None:
    path = _path_for(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if float(payload.get("expires_at", 0)) < time.time():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    return payload.get("value")


def write(key: str, value: Any, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
    path = _path_for(key)
    payload = {
        "key": key,
        "stored_at": int(time.time()),
        "expires_at": int(time.time()) + max(1, int(ttl_seconds)),
        "value": value,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


def clear() -> int:
    """Delete RepoScope cache files and return the number removed."""
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for path in CACHE_DIR.glob("*.json"):
        try:
            path.unlink()
            count += 1
        except OSError:
            continue
    return count
