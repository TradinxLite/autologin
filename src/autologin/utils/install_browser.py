"""
Playwright browser installation utility.
Ensures Chromium is installed on first run.
"""

import logging
import subprocess
import sys
from pathlib import Path


def is_browser_installed() -> bool:
    """
    Check if Playwright Chromium browser is installed.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to get the executable path - will fail if not installed
            path = p.chromium.executable_path
            return Path(path).exists() if path else False
    except Exception:
        return False


def install_browser(progress_callback=None) -> bool:
    """
    Install Playwright Chromium browser.
    
    Args:
        progress_callback: Optional callback function(message: str) for progress updates
        
    Returns:
        True if installation successful, False otherwise
    """
    def report(msg: str):
        logging.info(msg)
        if progress_callback:
            progress_callback(msg)
    
    report("Starting Playwright browser download...")
    
    try:
        # Run playwright install chromium
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for slow connections
        )
        
        if result.returncode == 0:
            report("Browser installation completed successfully!")
            return True
        else:
            report(f"Browser installation failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        report("Browser installation timed out. Please check your internet connection.")
        return False
    except Exception as e:
        report(f"Browser installation error: {str(e)}")
        return False


def ensure_browser_installed(progress_callback=None) -> bool:
    """
    Ensure browser is installed, installing if necessary.
    
    Args:
        progress_callback: Optional callback function(message: str) for progress updates
        
    Returns:
        True if browser is available, False otherwise
    """
    if is_browser_installed():
        return True
    
    return install_browser(progress_callback)


class BrowserInstaller:
    """
    Thread-safe browser installer with Qt signal support.
    Use this when installing from a Qt GUI.
    """
    
    def __init__(self):
        self._installed = None
        
    def check_and_install(self, progress_callback=None) -> bool:
        """Check if browser is installed, install if needed."""
        if self._installed is None:
            self._installed = is_browser_installed()
            
        if self._installed:
            return True
            
        self._installed = install_browser(progress_callback)
        return self._installed
