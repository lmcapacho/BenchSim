"""Simple update checker for BenchSim releases on GitHub."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from importlib import metadata
from pathlib import Path

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
    assets = [
        {
            "name": asset.get("name", ""),
            "url": asset.get("browser_download_url", ""),
            "size": int(asset.get("size", 0) or 0),
        }
        for asset in latest.get("assets", [])
    ]
    selected_asset = select_release_asset(assets)

    return {
        "ok": True,
        "update_available": update_available,
        "current_version": _normalize_version(current_version),
        "latest_version": latest_version,
        "release_name": latest.get("name") or latest.get("tag_name", latest_version),
        "release_url": latest.get("html_url", f"https://github.com/{GITHUB_REPO}/releases"),
        "assets": assets,
        "selected_asset": selected_asset,
    }


def select_release_asset(assets):
    """Pick the best release asset for current platform."""
    valid_assets = [item for item in assets if item.get("name") and item.get("url")]
    if not valid_assets:
        return None

    lowered = [(item["name"].lower(), item) for item in valid_assets]
    if sys.platform.startswith("win"):
        patterns = ("windows-x64-setup.exe", "windows-x64-portable.zip", ".exe", ".zip")
    elif sys.platform.startswith("linux"):
        patterns = ("linux-x86_64.tar.gz", ".tar.gz", ".zip")
    else:
        patterns = (".zip", ".tar.gz", ".exe")

    for pattern in patterns:
        for name, item in lowered:
            if pattern in name or name.endswith(pattern):
                return item
    return valid_assets[0]


def get_update_download_dir():
    """Return writable directory for update package downloads."""
    if sys.platform.startswith("win"):
        base_dir = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform.startswith("darwin"):
        base_dir = os.path.expanduser("~/Library/Caches")
    else:
        base_dir = os.path.expanduser("~/.cache")
    return str(Path(base_dir) / "BenchSim" / "updates")


def download_asset(asset, dest_dir=None, timeout=45):
    """Download one release asset and return local file path."""
    if not asset or not asset.get("url") or not asset.get("name"):
        raise ValueError("Invalid update asset.")

    target_dir = Path(dest_dir or get_update_download_dir())
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / asset["name"]

    request = urllib.request.Request(
        asset["url"],
        headers={"Accept": "application/octet-stream", "User-Agent": "BenchSim"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    with open(destination, "wb") as file:
        file.write(data)
    return str(destination)


def launch_installer(package_path):
    """Launch downloaded installer/package. Returns True if launch was attempted."""
    if not package_path:
        return False
    path = str(package_path)
    lower = path.lower()

    if sys.platform.startswith("win") and lower.endswith(".exe"):
        subprocess.Popen([path], shell=True)  # pylint: disable=consider-using-with
        return True

    if sys.platform.startswith("linux"):
        opener = "xdg-open"
        if shutil.which(opener):
            subprocess.Popen([opener, os.path.dirname(path) or "."])  # pylint: disable=consider-using-with
            return True
    return False
