"""Update-check service tests."""

import time

import pytest

from app.services import update_service


def test_tag_to_version_strips_prefix():
    assert update_service._tag_to_version("v0.2.0") == "0.2.0"
    assert update_service._tag_to_version("V1.0.0") == "1.0.0"
    assert update_service._tag_to_version("0.3.1") == "0.3.1"


@pytest.mark.parametrize(
    "latest, current, expected",
    [
        ("0.3.0", "0.2.0", True),
        ("0.2.1", "0.2.0", True),
        ("1.0.0", "0.9.9", True),
        ("0.2.0", "0.2.0", False),
        ("0.1.9", "0.2.0", False),
        ("0.10.0", "0.9.0", True),
    ],
)
def test_is_newer(latest, current, expected):
    assert update_service.is_newer(latest, current) is expected


def test_check_for_update_handles_no_release(monkeypatch):
    """When GitHub returns no payload (404 / network error), return safe defaults."""
    monkeypatch.setattr(update_service, "_fetch_release", lambda: None)
    update_service._cache["payload"] = None
    update_service._cache["fetched_at"] = 0.0

    result = update_service.check_for_update(force=True)

    assert result["current_version"] == update_service.APP_VERSION
    assert result["latest_version"] is None
    assert result["has_update"] is False
    assert "releases" in result["release_url"]
    assert result["assets"] == []


def test_check_for_update_detects_new_version(monkeypatch):
    payload = {
        "tag_name": "v9.9.9",
        "html_url": "https://github.com/x/y/releases/tag/v9.9.9",
        "body": "## What's new\n- stuff",
        "assets": [
            {"name": "PersonalPM-Setup-9.9.9.exe", "size": 123, "browser_download_url": "https://x"}
        ],
    }
    monkeypatch.setattr(update_service, "_fetch_release", lambda: payload)
    update_service._cache["payload"] = None
    update_service._cache["fetched_at"] = 0.0

    result = update_service.check_for_update(force=True)

    assert result["has_update"] is True
    assert result["latest_version"] == "9.9.9"
    assert result["release_notes"] == "## What's new\n- stuff"
    assert result["assets"][0]["name"] == "PersonalPM-Setup-9.9.9.exe"


def test_check_for_update_uses_cache(monkeypatch):
    """If the cache is fresh, _fetch_release must NOT be called."""
    calls = {"n": 0}

    def fake_fetch():
        calls["n"] += 1
        return None

    monkeypatch.setattr(update_service, "_fetch_release", fake_fetch)
    update_service._cache["payload"] = {"tag_name": "v0.2.0"}
    update_service._cache["fetched_at"] = time.time()  # fresh

    update_service.check_for_update(force=False)
    assert calls["n"] == 0

    update_service.check_for_update(force=True)
    assert calls["n"] == 1


def test_endpoint_returns_update_payload(client, monkeypatch):
    payload = {
        "tag_name": "v99.0.0",
        "html_url": "https://github.com/x/y/releases/tag/v99.0.0",
        "body": "release notes",
        "assets": [],
    }
    monkeypatch.setattr(update_service, "_fetch_release", lambda: payload)
    update_service._cache["payload"] = None
    update_service._cache["fetched_at"] = 0.0

    r = client.get("/api/updates/check?force=1")
    assert r.status_code == 200
    data = r.json()
    assert data["has_update"] is True
    assert data["latest_version"] == "99.0.0"
