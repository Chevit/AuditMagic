"""GitHub release update checker for AuditMagic."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from logger import logger
from version import __version__

GITHUB_API_URL = "https://api.github.com/repos/Chevit/AuditMagic/releases/latest"
REQUEST_TIMEOUT = 10  # seconds
MAX_RESPONSE_SIZE = 512 * 1024  # 512 KB — guard against oversized responses


@dataclass
class UpdateInfo:
    """Information about an available update."""

    version: str
    download_url: str
    release_notes: str
    html_url: str  # GitHub release page URL


def check_for_update() -> Optional[UpdateInfo]:
    """Check GitHub for a newer release.

    Returns:
        UpdateInfo if a newer version is available, None otherwise.
    """
    try:
        logger.info(f"Checking for updates (current: {__version__})...")

        request = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AuditMagic-UpdateChecker",
            },
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read(MAX_RESPONSE_SIZE).decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        latest_version = latest_tag.lstrip("v")

        if not latest_version:
            logger.warning("No version tag found in latest release")
            return None

        if _is_newer(latest_version, __version__):
            # Find the .exe asset
            download_url = ""
            for asset in data.get("assets", []):
                if asset["name"].lower().endswith(".exe"):
                    url = asset.get("browser_download_url", "")
                    if url.startswith("https://"):
                        download_url = url
                    break

            info = UpdateInfo(
                version=latest_version,
                download_url=download_url,
                release_notes=data.get("body", "") or "",
                html_url=data.get("html_url", ""),
            )
            logger.info(f"Update available: {latest_version}")
            return info

        logger.info("Application is up to date")
        return None

    except urllib.error.URLError as e:
        logger.warning(f"Network error checking for updates: {e}")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Error parsing update response: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error checking for updates: {e}")
        return None


def _is_newer(latest: str, current: str) -> bool:
    """Compare version strings (semantic versioning).

    Args:
        latest: Latest version string (e.g., "1.2.0").
        current: Current version string.

    Returns:
        True if latest is newer than current.
    """
    try:
        latest_parts = [int(x) for x in latest.split(".")]
        current_parts = [int(x) for x in current.split(".")]
        return latest_parts > current_parts
    except (ValueError, AttributeError):
        return False
