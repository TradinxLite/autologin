"""
Playwright browser installation utility.
Ensures Chromium is installed on first run.
Handles both development and packaged (Briefcase) environments.
"""

import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_playwright_browsers_path() -> Path:
    """
    Get the path where Playwright browsers should be installed.
    For packaged apps, this is within the app's data directory.
    """
    from platformdirs import user_data_dir
    return Path(user_data_dir(appname="AutoLogin")) / "playwright-browsers"


def is_browser_installed() -> bool:
    """
    Check if Playwright Chromium browser is installed.
    """
    try:
        # Set environment variable to use our custom browser path
        browsers_path = get_playwright_browsers_path()
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
        
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to get the executable path - will fail if not installed
            path = p.chromium.executable_path
            if path and Path(path).exists():
                logging.info(f"Browser found at: {path}")
                return True
            return False
    except Exception as e:
        logging.debug(f"Browser check failed: {e}")
        return False


def find_playwright_cli() -> list:
    """
    Find the best way to run playwright CLI.
    Returns the command as a list suitable for subprocess.
    """
    # Method 1: Try using playwright module directly with current Python
    # This works in development and some packaged scenarios
    
    # Method 2: Try finding playwright executable in PATH or pip user scripts
    playwright_exe = shutil.which("playwright")
    if playwright_exe:
        return [playwright_exe]
    
    # Method 3: On Windows, check common locations
    if platform.system() == "Windows":
        # Check user scripts directory
        user_base = os.path.expanduser("~")
        possible_paths = [
            Path(user_base) / "AppData" / "Local" / "Programs" / "Python" / "Python311" / "Scripts" / "playwright.exe",
            Path(user_base) / "AppData" / "Local" / "Programs" / "Python" / "Python310" / "Scripts" / "playwright.exe",
            Path(user_base) / "AppData" / "Roaming" / "Python" / "Python311" / "Scripts" / "playwright.exe",
            Path(user_base) / "AppData" / "Roaming" / "Python" / "Python310" / "Scripts" / "playwright.exe",
        ]
        for p in possible_paths:
            if p.exists():
                return [str(p)]
    
    # Method 4: Use python -m playwright (fallback)
    # WARNING: Do NOT use this if running as a packaged app (sys.executable is the app itself)
    if not is_packaged_app():
        return [sys.executable, "-m", "playwright"]
        
    logging.warning("Cannot use python -m playwright in packaged app: no python executable available")
    return []


def install_browser_via_python_api(progress_callback=None) -> bool:
    """
    Try installing browser using Playwright's Python API directly.
    This bypasses subprocess issues in packaged apps.
    """
    def report(msg: str):
        logging.info(msg)
        if progress_callback:
            progress_callback(msg)
    
    try:
        report("Attempting direct browser installation...")
        
        # Set custom browser path
        browsers_path = get_playwright_browsers_path()
        browsers_path.mkdir(parents=True, exist_ok=True)
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
        
        # Try using playwright's internal install mechanism
        from playwright._impl._driver import compute_driver_executable
        from playwright._impl._driver import get_driver_env
        
        driver_executable = compute_driver_executable()
        report(f"Computed driver executable: {driver_executable}")
        
        # Unpack tuple (node_path, cli_path)
        if isinstance(driver_executable, tuple):
            node_path, cli_path = driver_executable
        else:
            # Fallback for older versions?
            node_path, cli_path = driver_executable, None

        # Verify if driver exists
        if not os.path.exists(node_path):
            report(f"Node executable missing at: {node_path}")
            report("Searching for node executable in app directories...")
            
            # Manual search for node.exe/node in site-packages/playwright
            found_driver = find_manual_driver()
            if found_driver:
                node_path = found_driver
                report(f"Found driver manually at: {node_path}")
            else:
                report("Could not find node executable anywhere.")

        env = get_driver_env()
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
        
        report(f"Installing Chromium to: {browsers_path}")
        
        # Ensure executable permission for driver
        try:
            os.chmod(node_path, 0o755)
        except Exception:
            pass
            
        # Construct command: node cli.js install chromium
        cmd = [str(node_path)]
        if cli_path:
            cmd.append(str(cli_path))
        else:
            # If cli_path wasn't returned, we might need to assume it?
            # Playwright usually returns (node, cli) always.
            cmd.append("install") # Wait, if no cli path, this is wrong.
            # But compute_driver_executable() returns tuple.
            pass
            
        cmd.extend(["install", "chromium"])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=600
        )
        
        if result.returncode == 0:
            report("Browser installation completed successfully!")
            
            # Verify and fix permissions
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    exe_path = p.chromium.executable_path
                    if exe_path and os.path.exists(exe_path):
                        report(f"Verifying permissions for: {exe_path}")
                        # Ensure executable has +x perms
                        st = os.stat(exe_path)
                        os.chmod(exe_path, st.st_mode | 0o111)
            except Exception as e:
                logging.warning(f"Permission fix failed: {e}")
                
            return True
        else:
            logging.warning(f"Driver install failed: {result.stderr}")
            return False


            
    except ImportError as e:
        logging.warning(f"Could not import playwright internals: {e}")
        return False
    except Exception as e:
        logging.warning(f"Direct installation failed: {e}")
        # Check if it was the specific 'node' missing error
        str_e = str(e)
        if "No such file" in str_e and "driver" in str_e:
             logging.error("CRITICAL: Playwright driver/node executable is missing. "
                           "The application packaging may be incomplete.")
        return False


def find_manual_driver():
    """Search for the playwright node driver in common locations."""
    node_name = "node.exe" if sys.platform == "win32" else "node"
    
    # 1. Search in playwright package location
    try:
        import playwright
        package_root = Path(playwright.__file__).parent
        
        # Standard location: driver/package/node_modules/playwright-core/.local-browsers/
        # Standard location: driver/node
        driver_dir = package_root / "driver"
        possible_path = driver_dir / node_name
        if possible_path.exists():
            return str(possible_path)
            
        # Recursive search in package
        for path in package_root.rglob(node_name):
            return str(path)
            
    except ImportError:
        pass
        
    # 2. Search in sys.executable directory (sometimes bundled there)
    try:
        base_dir = Path(sys.executable).parent
        possible_path = base_dir / node_name
        if possible_path.exists():
            return str(possible_path)
            
        # Recursive search in app dir
        for path in base_dir.rglob(node_name):
            return str(path)
    except Exception:
        pass
        
    return None


def is_packaged_app() -> bool:
    """Check if running as a packaged/frozen application."""
    if getattr(sys, 'frozen', False):
        return True
    
    # Briefcase specific check (sys.executable points to the app bundle, not python)
    # Checking if executable name looks like python
    exe_name = Path(sys.executable).name.lower()
    if 'python' not in exe_name and exe_name != 'jb_python':
        return True
        
    return False


def install_browser_via_cli(progress_callback=None) -> bool:
    """
    Install browser using playwright CLI subprocess.
    """
    def report(msg: str):
        logging.info(msg)
        if progress_callback:
            progress_callback(msg)
    
    # Set custom browser path
    browsers_path = get_playwright_browsers_path()
    browsers_path.mkdir(parents=True, exist_ok=True)
    
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
    
    cmd = find_playwright_cli()
    if not cmd:
        report("Could not find Playwright CLI and cannot run python -m playwright.")
        return False
        
    cmd = cmd + ["install", "chromium"]
    report(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
            # On Windows, hide the console window
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        
        if result.returncode == 0:
            report("Browser installation completed successfully!")
            return True
        else:
            report(f"Browser installation failed: {result.stderr}")
            logging.error(f"Playwright install stderr: {result.stderr}")
            logging.error(f"Playwright install stdout: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        report("Browser installation timed out. Please check your internet connection.")
        return False
    except Exception as e:
        report(f"Browser installation error: {str(e)}")
        logging.exception("CLI installation failed")
        return False


def install_browser(progress_callback=None) -> bool:
    """
    Install Playwright Chromium browser.
    Tries multiple methods for maximum compatibility.
    
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
    
    # Ensure browsers path exists
    browsers_path = get_playwright_browsers_path()
    browsers_path.mkdir(parents=True, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
    
    # Method 1: Try using Playwright's internal driver (most reliable for packaged apps)
    report("Trying installation method 1 (internal driver)...")
    if install_browser_via_python_api(progress_callback):
        return True
    
    # Method 2: Try CLI-based installation
    report("Trying installation method 2 (CLI)...")
    if install_browser_via_cli(progress_callback):
        return True
    
    # All methods failed
    report("All installation methods failed. Please install browser manually.")
    logging.error(f"Failed to install Playwright browser. Browsers path: {browsers_path}")
    return False


def ensure_browser_installed(progress_callback=None) -> bool:
    """
    Ensure browser is installed, installing if necessary.
    
    Args:
        progress_callback: Optional callback function(message: str) for progress updates
        
    Returns:
        True if browser is available, False otherwise
    """
    # Set the browsers path environment variable first
    browsers_path = get_playwright_browsers_path()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
    
    if is_browser_installed():
        logging.info("Playwright browser already installed")
        return True
    
    logging.info("Playwright browser not found, starting installation...")
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
