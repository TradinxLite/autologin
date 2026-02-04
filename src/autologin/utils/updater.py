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
# Try to import packaging, but define fallback if missing
try:
    from packaging import version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False

logger = logging.getLogger(__name__)

# Configuration
GITHUB_REPO = "TradinxLite/autologin"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Hardcoded version as fallback (updated during build)
APP_VERSION = "1.0.15"


def get_current_version() -> str:
    """Get the current application version."""
    try:
        # First try to get from package metadata
        import importlib.metadata
        return importlib.metadata.version("autologin")
    except Exception:
        pass
    
    # Fallback to hardcoded version
    return APP_VERSION


def parse_version_fallback(v_str: str) -> tuple:
    """
    Parse version string to tuple of integers for comparison.
    Handles '1.0.0', 'v1.0.0', '1.0', etc.
    """
    try:
        # Strip leading v
        v_str = v_str.lstrip('v').strip()
        # Split by dot and convert to int (ignoring non-numeric parts like -beta)
        parts = []
        for part in v_str.split('.'):
            # Extract numeric part
            num = ''.join(c for c in part if c.isdigit())
            if num:
                parts.append(int(num))
        return tuple(parts)
    except Exception:
        return (0, 0, 0)


def is_version_newer(latest: str, current: str) -> bool:
    """
    Compare versions using packaging if available, or fallback logic.
    Returns True if latest > current.
    """
    if HAS_PACKAGING:
        try:
            return version.parse(latest) > version.parse(current)
        except Exception:
            logger.warning("Packaging version comparison failed, using fallback")
    
    # Fallback comparison
    try:
        return parse_version_fallback(latest) > parse_version_fallback(current)
    except Exception as e:
        logger.error(f"Version comparison failed: {e}")
        return False


def get_platform_info() -> Tuple[str, str]:
    """Get platform system and machine info."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    return system, machine


def get_platform_asset_suffix() -> str:
    """Get the expected asset file extension for the current platform."""
    system, _ = get_platform_info()
    
    if system == "darwin":
        return ".dmg"
    elif system == "windows":
        return ".msi"
    elif system == "linux":
        return ".AppImage"
    return ""


def find_platform_asset(assets: list) -> Optional[dict]:
    """
    Find the correct asset for the current platform from the release assets.
    """
    system, machine = get_platform_info()
    suffix = get_platform_asset_suffix()
    
    if not suffix:
        return None
    
    # Find assets matching our platform
    matching_assets = []
    
    for asset in assets:
        name = asset.get("name", "").lower()
        
        # Must have correct extension
        if not name.endswith(suffix.lower()):
            continue
        
        # Platform-specific checks
        if system == "darwin":
            if "macos" in name or "darwin" in name or name.endswith(".dmg"):
                matching_assets.append(asset)
        elif system == "windows":
            if "windows" in name or "win" in name or name.endswith(".msi"):
                matching_assets.append(asset)
        elif system == "linux":
            if "linux" in name or "appimage" in name.lower():
                # Check architecture
                if "arm" in machine or "aarch64" in machine:
                    if "arm" in name or "aarch64" in name:
                        matching_assets.append(asset)
                else:
                    # x86_64 - exclude arm builds
                    if "arm" not in name and "aarch64" not in name:
                        matching_assets.append(asset)
    
    # Return first matching asset
    return matching_assets[0] if matching_assets else None


def check_for_updates() -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Check GitHub for the latest release.
    """
    try:
        logger.info("Checking for updates...")
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        release_data = response.json()
        tag_name = release_data.get("tag_name", "")
        latest_version = tag_name.lstrip("v")
        release_notes = release_data.get("body", "")
        
        current = get_current_version()
        
        logger.info(f"Current version: {current}, Latest version: {latest_version}")
        
        if not latest_version:
            logger.warning("Could not determine latest version from release")
            return False, None, None, None
        
        # Compare versions
        if is_version_newer(latest_version, current):
            logger.info("Update available!")
            
            # Find the appropriate asset for this platform
            asset = find_platform_asset(release_data.get("assets", []))
            
            if asset:
                download_url = asset.get("browser_download_url")
                logger.info(f"Found download URL: {download_url}")
                return True, latest_version, download_url, release_notes
            else:
                logger.warning("No suitable asset found for this platform")
                return True, latest_version, None, release_notes
        else:
            logger.info("No update available - current version is up to date")
            return False, latest_version, None, None
        
    except requests.RequestException as e:
        logger.warning(f"Failed to check for updates: {e}")
        return False, None, None, str(e)
    except Exception as e:
        logger.error(f"Unexpected error checking for updates: {e}")
        return False, None, None, str(e)


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
        logger.info(f"Downloading update from: {download_url}")
        
        response = requests.get(download_url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get("content-length", 0))
        
        # Create temp file with appropriate extension
        suffix = Path(download_url).suffix or ".zip"
        # Ensure the suffix is valid
        if suffix not in [".msi", ".dmg", ".AppImage", ".zip", ".exe", ".deb"]:
            suffix = ".zip"
        
        # Use a proper download directory
        download_dir = Path(tempfile.gettempdir()) / "autologin_updates"
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract filename from URL
        filename = Path(download_url).name
        temp_file = download_dir / filename
        
        downloaded = 0
        chunk_size = 8192
        
        logger.info(f"Downloading to: {temp_file}")
        
        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
        
        logger.info(f"Download complete: {temp_file}")
        return temp_file
        
    except Exception as e:
        logger.error(f"Failed to download update: {e}")
        return None


def apply_update(update_file: Path) -> bool:
    """
    Apply the downloaded update.
    Platform-specific installation logic.
    """
    system, _ = get_platform_info()
    
    try:
        logger.info(f"Applying update from: {update_file}")
        
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
        # Use ShellExecute to run with proper permissions
        logger.info(f"Launching Windows installer: {update_file}")
        
        # Start the installer and exit the app
        # Using os.startfile for proper Windows handling
        try:
            os.startfile(str(update_file))
            return True
        except Exception:
            # Fallback to subprocess
            subprocess.Popen([str(update_file)], shell=True)
            return True
    return False


def _apply_linux_update(update_file: Path) -> bool:
    """Apply update on Linux."""
    # For .AppImage files
    if "AppImage" in update_file.name or update_file.suffix == ".AppImage":
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
        on_error: Optional[Callable[[str], None]] = None,
        on_checking: Optional[Callable[[], None]] = None
    ):
        self.on_update_available = on_update_available
        self.on_no_update = on_no_update
        self.on_error = on_error
        self.on_checking = on_checking
        self._thread: Optional[threading.Thread] = None
    
    def check_async(self):
        """Check for updates in a background thread."""
        if self.on_checking:
            self.on_checking()
        self._thread = threading.Thread(target=self._check_worker, daemon=True)
        self._thread.start()
    
    def _check_worker(self):
        """Worker function for background update check."""
        try:
            has_update, new_version, url, notes = check_for_updates()
            
            if has_update and self.on_update_available:
                self.on_update_available(new_version, url, notes or "")
            elif not has_update and self.on_no_update:
                self.on_no_update()
        except Exception as e:
            logger.exception("Update check failed")
            if self.on_error:
                self.on_error(str(e))
