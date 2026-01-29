"""
Auto-updater module for AutoLogin application.
Checks GitHub Releases for updates and handles download/installation.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional, Tuple, Callable

import requests
from packaging import version

logger = logging.getLogger(__name__)

# Configuration
GITHUB_REPO = "TradinxLite/autologin"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_current_version() -> str:
    """Get the current application version from package metadata."""
    try:
        import importlib.metadata
        return importlib.metadata.version("autologin")
    except Exception:
        return "0.0.0"


def get_platform_asset_pattern() -> str:
    """Get the expected asset filename pattern for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        return "AutoLogin-macos"
    elif system == "windows":
        return "AutoLogin-windows"
    elif system == "linux":
        if "arm" in machine or "aarch64" in machine:
            return "AutoLogin-linux-arm"
        return "AutoLogin-linux"
    return ""


def check_for_updates() -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Check GitHub for the latest release.
    
    Returns:
        Tuple of (update_available, latest_version, download_url, release_notes)
    """
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        release_data = response.json()
        latest_version = release_data.get("tag_name", "").lstrip("v")
        release_notes = release_data.get("body", "")
        
        current = get_current_version()
        
        if not latest_version:
            return False, None, None, None
        
        # Compare versions
        try:
            if version.parse(latest_version) > version.parse(current):
                # Find the appropriate asset for this platform
                pattern = get_platform_asset_pattern()
                download_url = None
                
                for asset in release_data.get("assets", []):
                    if pattern and pattern in asset.get("name", ""):
                        download_url = asset.get("browser_download_url")
                        break
                
                return True, latest_version, download_url, release_notes
        except Exception as e:
            logger.warning(f"Version comparison failed: {e}")
        
        return False, latest_version, None, None
        
    except requests.RequestException as e:
        logger.warning(f"Failed to check for updates: {e}")
        return False, None, None, None
    except Exception as e:
        logger.error(f"Unexpected error checking for updates: {e}")
        return False, None, None, None


def download_update(
    download_url: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Optional[Path]:
    """
    Download the update file.
    
    Args:
        download_url: URL to download from
        progress_callback: Optional callback(downloaded_bytes, total_bytes)
    
    Returns:
        Path to downloaded file, or None on failure
    """
    try:
        response = requests.get(download_url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get("content-length", 0))
        
        # Create temp file with appropriate extension
        suffix = Path(download_url).suffix or ".zip"
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix="autologin_update_"
        )
        
        downloaded = 0
        chunk_size = 8192
        
        with open(temp_file.name, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
        
        return Path(temp_file.name)
        
    except Exception as e:
        logger.error(f"Failed to download update: {e}")
        return None


def apply_update(update_file: Path) -> bool:
    """
    Apply the downloaded update.
    Platform-specific installation logic.
    """
    system = platform.system().lower()
    
    try:
        if system == "darwin":
            return _apply_macos_update(update_file)
        elif system == "windows":
            return _apply_windows_update(update_file)
        elif system == "linux":
            return _apply_linux_update(update_file)
        return False
    except Exception as e:
        logger.error(f"Failed to apply update: {e}")
        return False


def _apply_macos_update(update_file: Path) -> bool:
    """Apply update on macOS."""
    # For .dmg files, open them for user to drag to Applications
    if update_file.suffix == ".dmg":
        subprocess.run(["open", str(update_file)])
        return True
    # For .app.zip files, extract and replace
    elif update_file.suffix == ".zip":
        subprocess.run(["open", str(update_file)])
        return True
    return False


def _apply_windows_update(update_file: Path) -> bool:
    """Apply update on Windows."""
    # Launch installer
    if update_file.suffix in [".msi", ".exe"]:
        subprocess.Popen([str(update_file)], shell=True)
        return True
    return False


def _apply_linux_update(update_file: Path) -> bool:
    """Apply update on Linux."""
    # For .AppImage files
    if "AppImage" in update_file.name:
        # Make executable and open containing directory
        update_file.chmod(0o755)
        subprocess.run(["xdg-open", str(update_file.parent)])
        return True
    # For .deb files
    elif update_file.suffix == ".deb":
        subprocess.run(["xdg-open", str(update_file)])
        return True
    return False


class UpdateChecker:
    """Background update checker with callbacks."""
    
    def __init__(
        self,
        on_update_available: Optional[Callable[[str, str, str], None]] = None,
        on_no_update: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        self.on_update_available = on_update_available
        self.on_no_update = on_no_update
        self.on_error = on_error
        self._thread: Optional[threading.Thread] = None
    
    def check_async(self):
        """Check for updates in a background thread."""
        self._thread = threading.Thread(target=self._check_worker, daemon=True)
        self._thread.start()
    
    def _check_worker(self):
        """Worker function for background update check."""
        try:
            has_update, new_version, url, notes = check_for_updates()
            
            if has_update and self.on_update_available:
                self.on_update_available(new_version, url, notes)
            elif not has_update and self.on_no_update:
                self.on_no_update()
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
