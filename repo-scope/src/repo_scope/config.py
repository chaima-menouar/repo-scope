"""Runtime configuration for RepoScope."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API_BASE = os.environ.get("GITHUB_API_BASE", "https://api.github.com").rstrip("/")
GITHUB_API_VERSION = os.environ.get("GITHUB_API_VERSION", "2026-03-10")
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
GITHUB_MAX_PAGES = int(os.environ.get("GITHUB_MAX_PAGES", "3"))
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "15"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")

if os.environ.get("VERCEL"):
    CACHE_DIR = Path(os.environ.get("REPO_SCOPE_CACHE_DIR", "/tmp/repo_scope_cache"))
else:
    CACHE_DIR = Path(os.environ.get("REPO_SCOPE_CACHE_DIR", str(PROJECT_ROOT / "db")))
