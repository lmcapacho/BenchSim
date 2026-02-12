"""Simple update checker for BenchSim releases on GitHub."""

from __future__ import annotations

import json
import re
import urllib.request
from importlib import metadata

GITHUB_REPO = "lmcapacho/BenchSim"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"


def get_current_version(default="0.0.0"):
    """Return installed package version."""
    try:
        return metadata.version("benchsim")
    except Exception:
        return default


def _parse_version(version_text):
    """Parse versions like 0.1.0, 0.1.0rc1, 0.1.0-rc1 into comparable tuple."""
    raw = version_text.strip().lower()
    if raw.startswith("v"):
        raw = raw[1:]

    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-?rc(\d+))?$", raw)
    if not match:
        return None

    major, minor, patch, rc = match.groups()
    major, minor, patch = int(major), int(minor), int(patch)
    if rc is None:
        # Stable release ranks above release candidates.
        return major, minor, patch, 1, 0

    return major, minor, patch, 0, int(rc)


def _normalize_version(version_text):
    raw = version_text.strip()
    if raw.lower().startswith("v"):
        raw = raw[1:]
    return raw


def check_for_updates(current_version, include_prerelease=False, timeout=4):
    """Check GitHub releases and return update metadata."""
    current_key = _parse_version(current_version)
    if current_key is None:
        return {
            "ok": False,
            "error": f"Unsupported current version format: {current_version}",
        }

    request = urllib.request.Request(
        RELEASES_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "BenchSim"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    latest = None
    latest_key = None
    for release in data:
        if release.get("draft"):
            continue
        if release.get("prerelease") and not include_prerelease:
            continue

        tag = release.get("tag_name", "")
        parsed = _parse_version(tag)
        if parsed is None:
            continue

        if latest_key is None or parsed > latest_key:
            latest_key = parsed
            latest = release

    if latest is None:
        return {"ok": False, "error": "No valid release found."}

    latest_version = _normalize_version(latest.get("tag_name", "0.0.0"))
    update_available = latest_key > current_key

    return {
        "ok": True,
        "update_available": update_available,
        "current_version": _normalize_version(current_version),
        "latest_version": latest_version,
        "release_name": latest.get("name") or latest.get("tag_name", latest_version),
        "release_url": latest.get("html_url", f"https://github.com/{GITHUB_REPO}/releases"),
    }
