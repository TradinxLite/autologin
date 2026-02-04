"""
Playwright-based browser automation driver.
Replaces Selenium/undetected_chromedriver with Playwright for more stable browser automation.
"""

import asyncio
import os
import logging
import psutil
from pathlib import Path
from platformdirs import user_data_dir
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from autologin.workers.stealth import get_stealth_scripts


def get_data_dir():
    """Get the application data directory."""
    return Path(user_data_dir(appname="AutoLogin")) / "data"


def get_playwright_browsers_path() -> Path:
    """Get the path where Playwright browsers are installed."""
    return Path(user_data_dir(appname="AutoLogin")) / "playwright-browsers"


def setup_playwright_environment():
    """Set up environment variables for Playwright."""
    browsers_path = get_playwright_browsers_path()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)


def detect_optimal_concurrency() -> int:
    """
    Detect optimal concurrency based on system resources.
    
    Rules:
    - Base: 1 worker per 2GB RAM available (minimum 2GB reserved for system)
    - Cap at CPU cores (to avoid context switching overhead)
    - Minimum: 2, Maximum: 15
    
    Each browser context uses approximately:
    - 150-300MB RAM in headless mode
    - 300-500MB RAM in headed mode
    """
    try:
        # Get available memory in GB
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024 ** 3)
        
        # Reserve 2GB for system, use 500MB per worker as estimate
        usable_memory = max(0, available_gb - 2)
        memory_based_workers = int(usable_memory / 0.5)
        
        # Get CPU count
        cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count() or 4
        
        # Calculate optimal - minimum of memory and CPU based limits
        optimal = min(memory_based_workers, cpu_count)
        
        # Clamp between 2 and 15
        return max(2, min(15, optimal))
    except Exception:
        # Fallback to safe default
        return 4


class PlaywrightDriver:
    """
    Manages Playwright browser instances with stealth settings.
    Designed for concurrent execution of multiple login flows.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Playwright = None
        self._browser: Browser = None
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        
    async def start(self):
        """Initialize Playwright and launch browser."""
        # Ensure Playwright knows where to find browsers
        setup_playwright_environment()
        
        self._playwright = await async_playwright().start()
        
        # Launch Chromium with stealth settings
        try:
            # Diagnostic: verify browser path
            executable_path = self._playwright.chromium.executable_path
            logging.info(f"Attempting to launch browser from: {executable_path}")
            
            if not os.path.exists(executable_path):
                logging.error(f"Browser executable not found at: {executable_path}")
                # Try to force re-install?
            
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-infobars',
                    '--start-maximized',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--exclude-switches=enable-automation',
                    '--use-fake-ui-for-media-stream',
                ]
            )
        except Exception as e:
            logging.error(f"Failed to launch browser: {e}")
            raise
        
    async def stop(self):
        """Clean up browser and Playwright instances."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            
    async def new_context(self, user_agent: str = None) -> BrowserContext:
        """
        Create a new isolated browser context with stealth settings.
        Each context is isolated (separate cookies, storage, etc.)
        """
        context_options = {
            'viewport': None,
            'ignore_https_errors': True,
        }
        
        if user_agent:
            context_options['user_agent'] = user_agent
        else:
            # Default realistic user agent
            context_options['user_agent'] = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            )
            
        context = await self._browser.new_context(**context_options)
        
        # Apply stealth scripts
        await self._apply_stealth(context)
        
        return context
    
    async def _apply_stealth(self, context: BrowserContext):
        # Apply stealth modifications from stealth module
        scripts = get_stealth_scripts()
        for script in scripts:
            await context.add_init_script(script)


async def wait_and_fill(page: Page, selector: str, value: str, timeout: int = 10000):
    """Wait for element and fill with value."""
    await page.wait_for_selector(selector, timeout=timeout)
    await page.fill(selector, value)


async def wait_and_click(page: Page, selector: str, timeout: int = 10000):
    """Wait for element and click."""
    await page.wait_for_selector(selector, timeout=timeout)
    await page.click(selector)


async def wait_for_text(page: Page, text: str, timeout: int = 15000) -> bool:
    """Wait for specific text to appear on page."""
    try:
        await page.wait_for_selector(f'text="{text}"', timeout=timeout)
        return True
    except Exception:
        return False


async def check_page_contains(page: Page, text: str) -> bool:
    """Check if page contains specific text."""
    content = await page.content()
    return text in content
