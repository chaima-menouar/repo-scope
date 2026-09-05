"""GitHub REST API client with pagination, caching, and rate-limit awareness."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import requests

from repo_scope.config import (
    CACHE_TTL_SECONDS,
    GITHUB_API_BASE,
    GITHUB_API_VERSION,
    GITHUB_MAX_PAGES,
    GITHUB_RATE_LIMIT_WAIT_MAX_SECONDS,
    GITHUB_TOKEN,
    REQUEST_TIMEOUT_SECONDS,
)
from repo_scope.fetch import cache


class GitHubAPIError(RuntimeError):
    """Raised when GitHub cannot satisfy a RepoScope request."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "RepoScope/0.6.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _friendly_error(response: requests.Response) -> str:
    try:
        detail = response.json().get("message", response.text)
    except ValueError:
        detail = response.text

    if response.status_code == 404:
        return "Repository not found, private, or inaccessible with the configured GitHub token."
    if response.status_code in {403, 429}:
        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")
        if remaining == "0" and reset:
            try:
                when = datetime.fromtimestamp(int(reset), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                return f"GitHub API rate limit reached. It resets at {when}. Add GITHUB_TOKEN for a higher limit."
            except (TypeError, ValueError, OSError):
                pass
        retry_after = response.headers.get("retry-after")
        if retry_after:
            return f"GitHub API asked us to slow down. Retry after {retry_after} seconds."
        return "GitHub API rate limit or abuse protection was triggered. Add GITHUB_TOKEN and retry later."
    return f"GitHub API returned {response.status_code}: {detail}"


def _rate_limit_wait_seconds(response: requests.Response) -> int | None:
    """Return a bounded retry delay for explicit GitHub throttling responses."""
    if response.status_code not in {403, 429}:
        return None

    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            return max(1, int(float(retry_after)))
        except (TypeError, ValueError):
            return None

    remaining = response.headers.get("x-ratelimit-remaining")
    reset = response.headers.get("x-ratelimit-reset")
    if remaining != "0" or not reset:
        return None
    try:
        return max(1, int(reset) - int(time.time()) + 5)
    except (TypeError, ValueError, OSError):
        return None


def _request(path_or_url: str, params: dict[str, Any] | None = None) -> requests.Response:
    url = path_or_url if path_or_url.startswith("http") else f"{GITHUB_API_BASE}{path_or_url}"

    for attempt in range(2):
        try:
            response = requests.get(url, headers=_headers(), params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise GitHubAPIError(f"Unable to reach GitHub: {exc}") from exc

        if response.status_code < 400:
            return response

        wait_seconds = _rate_limit_wait_seconds(response)
        if (
            attempt == 0
            and wait_seconds is not None
            and GITHUB_RATE_LIMIT_WAIT_MAX_SECONDS > 0
            and wait_seconds <= GITHUB_RATE_LIMIT_WAIT_MAX_SECONDS
        ):
            print(
                f"GitHub rate limit reached; waiting {wait_seconds}s before retrying {url}",
                flush=True,
            )
            time.sleep(wait_seconds)
            continue

        raise GitHubAPIError(_friendly_error(response), response.status_code)

    raise GitHubAPIError("GitHub request failed after a bounded rate-limit retry.")


def _cached_json(key: str, fetcher, *, use_cache: bool = True, ttl: int = CACHE_TTL_SECONDS):
    if use_cache:
        cached = cache.read(key)
        if cached is not None:
            return cached
    value = fetcher()
    if use_cache:
        cache.write(key, value, ttl)
    return value


def _paginate(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    max_pages: int = GITHUB_MAX_PAGES,
) -> list[dict]:
    items: list[dict] = []
    current_url = f"{GITHUB_API_BASE}{path}"
    current_params = {"per_page": 100, **(params or {})}

    for _ in range(max(1, max_pages)):
        response = _request(current_url, current_params)
        page = response.json()
        if not isinstance(page, list):
            raise GitHubAPIError("Unexpected GitHub pagination response.")
        items.extend(page)
        next_url = response.links.get("next", {}).get("url")
        if not next_url:
            break
        current_url = next_url
        current_params = None
    return items


def get_repo_info(owner: str, repo: str, *, use_cache: bool = True) -> dict:
    key = f"{owner}/{repo}/repo"
    return _cached_json(key, lambda: _request(f"/repos/{owner}/{repo}").json(), use_cache=use_cache)


def get_commits(owner: str, repo: str, since: str | None = None, *, use_cache: bool = True) -> list[dict]:
    key = f"{owner}/{repo}/commits/{since or 'recent'}"
    params = {"since": since} if since else {}
    return _cached_json(
        key,
        lambda: _paginate(f"/repos/{owner}/{repo}/commits", params),
        use_cache=use_cache,
    )


def get_contributors(owner: str, repo: str, *, use_cache: bool = True) -> list[dict]:
    key = f"{owner}/{repo}/contributors"
    return _cached_json(
        key,
        lambda: _paginate(f"/repos/{owner}/{repo}/contributors", {"anon": "1"}),
        use_cache=use_cache,
    )


def get_issues(owner: str, repo: str, state: str = "all", *, use_cache: bool = True) -> list[dict]:
    key = f"{owner}/{repo}/issues/{state}"

    def fetch() -> list[dict]:
        raw = _paginate(
            f"/repos/{owner}/{repo}/issues",
            {"state": state, "sort": "updated", "direction": "desc"},
        )
        return [item for item in raw if "pull_request" not in item]

    return _cached_json(key, fetch, use_cache=use_cache)


def get_pull_requests(owner: str, repo: str, state: str = "all", *, use_cache: bool = True) -> list[dict]:
    key = f"{owner}/{repo}/pulls/{state}"
    return _cached_json(
        key,
        lambda: _paginate(
            f"/repos/{owner}/{repo}/pulls",
            {"state": state, "sort": "updated", "direction": "desc"},
        ),
        use_cache=use_cache,
    )


def get_languages(owner: str, repo: str, *, use_cache: bool = True) -> dict:
    key = f"{owner}/{repo}/languages"
    return _cached_json(key, lambda: _request(f"/repos/{owner}/{repo}/languages").json(), use_cache=use_cache)


def get_latest_release(owner: str, repo: str, *, use_cache: bool = True) -> dict | None:
    """Return the latest GitHub release, or None when a repository has no releases."""
    key = f"{owner}/{repo}/latest-release"

    def fetch() -> dict | None:
        try:
            return _request(f"/repos/{owner}/{repo}/releases/latest").json()
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                return None
            raise

    return _cached_json(key, fetch, use_cache=use_cache, ttl=6 * 3600)


def get_repository_paths(
    owner: str,
    repo: str,
    default_branch: str,
    *,
    use_cache: bool = True,
) -> list[str]:
    """Return paths from the recursive git tree. Failure is intentionally non-fatal."""
    key = f"{owner}/{repo}/tree/{default_branch}"

    def fetch() -> list[str]:
        response = _request(f"/repos/{owner}/{repo}/git/trees/{default_branch}", {"recursive": "1"})
        payload = response.json()
        return [entry.get("path", "") for entry in payload.get("tree", []) if entry.get("path")]

    try:
        return _cached_json(key, fetch, use_cache=use_cache, ttl=6 * 3600)
    except GitHubAPIError:
        return []


def get_rate_limit() -> dict:
    response = _request("/rate_limit")
    return response.json()
