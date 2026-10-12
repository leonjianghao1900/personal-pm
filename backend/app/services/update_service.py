"""Check GitHub Releases for a newer version of Personal PM.

Cache: a single module-level cache, refreshed at most once per hour.
This keeps us well within the 60-req/hr unauthenticated GitHub API
budget even if every page load pings /api/updates/check.
"""
import json
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.version import APP_VERSION

GITHUB_REPO = "leonkangxi-dev/personal-pm"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASE_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
CACHE_TTL_SECONDS = 3600  # 1 hour

_cache: dict[str, object] = {"fetched_at": 0.0, "payload": None}


def _fetch_release() -> dict | None:
    """Hit GitHub's latest-release endpoint.  Returns parsed JSON or None."""
    req = Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"PersonalPM/{APP_VERSION}",
        },
    )
    with urlopen(req, timeout=5) as r:  # noqa: S310 - public API
        return json.loads(r.read().decode("utf-8"))


def _tag_to_version(tag: str) -> str:
    """Strip a leading 'v' / 'V' from a tag like 'v0.2.0' -> '0.2.0'."""
    return tag.lstrip("vV")


def _parse_tuple(v: str) -> tuple[int, ...]:
    out: list[int] = []
    for part in v.split("."):
        try:
            out.append(int(part))
        except ValueError:
            out.append(0)
    return tuple(out)


def is_newer(latest: str, current: str) -> bool:
    return _parse_tuple(latest) > _parse_tuple(current)


def _assets(release: dict | None) -> list[dict]:
    if not release:
        return []
    return [
        {"name": a.get("name"), "size": a.get("size"), "url": a.get("browser_download_url")}
        for a in release.get("assets", [])
    ]


def check_for_update(force: bool = False) -> dict:
    """Return update info for the current APP_VERSION.

    Shape:
      {
        "current_version": "0.2.0",
        "latest_version": "0.3.0" | None,
        "has_update": bool,
        "release_url": "...",
        "release_notes": "..." | None,
        "assets": [...],
        "checked_at": ISO-8601,
      }
    """
    now = time.time()
    payload = _cache.get("payload")
    fetched_at = _cache.get("fetched_at") or 0.0

    if force or payload is None or (now - fetched_at) > CACHE_TTL_SECONDS:
        try:
            payload = _fetch_release()
        except (URLError, TimeoutError, json.JSONDecodeError, OSError):
            payload = None
        _cache["payload"] = payload
        _cache["fetched_at"] = now

    latest_tag = (payload or {}).get("tag_name") or ""
    latest_version = _tag_to_version(latest_tag) if latest_tag else None
    has_update = bool(latest_version and is_newer(latest_version, APP_VERSION))

    return {
        "current_version": APP_VERSION,
        "latest_version": latest_version,
        "has_update": has_update,
        "release_url": (payload or {}).get("html_url") or RELEASE_PAGE,
        "release_notes": (payload or {}).get("body") if payload else None,
        "assets": _assets(payload),
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
    }
