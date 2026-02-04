
import sys
import logging
import platform
import os
from pathlib import Path

# Add src to path so we can import the module
current_dir = Path.cwd()
src_dir = current_dir / "src"
sys.path.append(str(src_dir))

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

try:
    from autologin.utils.updater import check_for_updates, get_current_version, get_platform_asset_suffix
    
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Asset Suffix: {get_platform_asset_suffix()}")
    print(f"Current Version (Internal): {get_current_version()}")
    
    print("\n--- Checking for updates ---")
    has_update, latest, url, notes = check_for_updates()
    
    print(f"\nResult:")
    print(f"Update Available: {has_update}")
    print(f"Latest Version: {latest}")
    print(f"Download URL: {url}")
    
    if not has_update and latest:
        print(f"\nNOTE: No update shown because Latest ({latest}) <= Current ({get_current_version()})")
    
    if has_update and not url:
        print("\nWARNING: Update available but no matching asset found for this platform!")

except ImportError as e:
    print(f"Error importing modules: {e}")
except Exception as e:
    print(f"Error checking updates: {e}")
