"""GitHub REST API client with retry, rate-limit handling, and caching headers."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15.0
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0


class GitHubClient:
    """Thin wrapper around the GitHub REST API."""

    BASE = "https://api.github.com"

    def __init__(self, token: str, timeout: float = _DEFAULT_TIMEOUT):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=self.BASE,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )
        self._etag_cache: dict[str, tuple[str, Any]] = {}  # url -> (etag, body)

    # ---- low-level ----

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Execute a request with retry + rate-limit back-off."""
        url = path if path.startswith("http") else path
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = self._client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                logger.warning("Transport error (attempt %d): %s", attempt, exc)
                if attempt == _MAX_RETRIES:
                    raise
                time.sleep(_BACKOFF_BASE * attempt)
                continue

            if resp.status_code == 304:
                return resp

            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset - int(time.time()), 1) if reset else 60
                logger.warning("Rate-limited. Sleeping %ds …", wait)
                time.sleep(wait)
                continue

            if resp.status_code in (429, 500, 502, 503, 504):
                sleep = _BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning("HTTP %d – retrying in %.1fs", resp.status_code, sleep)
                time.sleep(sleep)
                continue

            return resp

        return resp  # type: ignore[possibly-undefined]

    def get_json(self, path: str, params: dict | None = None) -> Any:
        """GET with ETag caching. Returns parsed JSON."""
        headers: dict[str, str] = {}
        cache_key = path + str(sorted((params or {}).items()))
        if cache_key in self._etag_cache:
            etag, cached_body = self._etag_cache[cache_key]
            headers["If-None-Match"] = etag

        resp = self._request("GET", path, params=params, headers=headers)

        if resp.status_code == 304 and cache_key in self._etag_cache:
            return self._etag_cache[cache_key][1]

        resp.raise_for_status()
        body = resp.json()

        etag_val = resp.headers.get("ETag")
        if etag_val:
            self._etag_cache[cache_key] = (etag_val, body)

        return body

    # ---- high-level helpers ----

    def get_repo(self, full_name: str) -> dict:
        return self.get_json(f"/repos/{full_name}")

    def get_readme(self, full_name: str) -> str:
        """Return decoded README text (best-effort)."""
        import base64
        try:
            data = self.get_json(f"/repos/{full_name}/readme")
            return base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        except httpx.HTTPStatusError:
            return ""

    def get_latest_release(self, full_name: str) -> Optional[dict]:
        try:
            return self.get_json(f"/repos/{full_name}/releases/latest")
        except httpx.HTTPStatusError:
            return None

    def search_repos(self, query: str, sort: str = "stars", per_page: int = 30, page: int = 1) -> list[dict]:
        data = self.get_json("/search/repositories", params={
            "q": query, "sort": sort, "order": "desc",
            "per_page": per_page, "page": page,
        })
        return data.get("items", [])

    def close(self):
        self._client.close()
