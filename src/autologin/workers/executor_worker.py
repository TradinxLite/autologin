"""
Executor Worker with concurrent login execution using Playwright.
Replaces the sequential Selenium-based executor with async concurrent processing.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot

from autologin.workers.playwright_driver import (
    PlaywrightDriver,
    detect_optimal_concurrency,
)
from autologin.workers.broker_logins import run_broker_login


class ExecutorWorker(QThread):
    """
    Worker thread that executes broker logins concurrently using Playwright.
    
    Signals:
        status: Emits status updates as dict with keys:
            - status: bool (success/failure)
            - message: str (status message)
            - do_refresh: bool (whether UI should refresh)
            - final_update: bool (optional, indicates completion)
        progress: Emits progress as (completed, total) tuple
    """
    
    status = pyqtSignal(dict)
    progress = pyqtSignal(int, int)

    def __init__(
        self,
        data_dir,
        all_login: bool = True,
        parent=None,
        is_headless: bool = True,
        max_concurrent: int = None,
        selected_accounts: List[Tuple[str, str]] = None  # List of (broker, client_id)
    ):
        """
        Initialize the executor worker.
        
        Args:
            data_dir: Path to application data directory
            all_login: If True, login all accounts. If False, only failed/logged-out accounts
            parent: Parent QObject
            is_headless: Run browser in headless mode
            max_concurrent: Maximum concurrent logins (auto-detect if None)
            selected_accounts: Optional list of (broker, client_id) to login specific accounts
        """
        super(ExecutorWorker, self).__init__(parent)
        self.data_dir = data_dir
        self.all_login = all_login
        self.is_headless = is_headless
        self.max_concurrent = max_concurrent or detect_optimal_concurrency()
        self.selected_accounts = selected_accounts
        self._stop_requested = False
        
    def request_stop(self):
        """Request the worker to stop gracefully."""
        self._stop_requested = True

    @pyqtSlot(dict)
    def handle_data_from_main_thread(self, data):
        """Handle commands from main thread."""
        logging.debug(f"Worker received data from main thread: {data}")
        action = data.get("action")
        if action == "stop":
            self.request_stop()

    def run(self):
        """Main entry point - runs the async login process."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self._run_concurrent_logins())
            finally:
                loop.close()
                
        except Exception as e:
            logging.error(f"ExecutorWorker error: {e}")
            self.status.emit({
                "status": False,
                "message": f"Executor error: {str(e)}",
                "do_refresh": False,
            })
        finally:
            logging.info("ExecutorWorker finished")

    async def _run_concurrent_logins(self):
        """
        Execute all broker logins concurrently with semaphore-based throttling.
        """
        path = f"{self.data_dir}/accounts.json"
        
        # Load accounts
        try:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump({}, f)
            with open(path, "r") as f:
                accounts = json.load(f) or {}
        except Exception as e:
            logging.error(f"Error reading accounts.json: {e}")
            accounts = {}
            
        if not accounts:
            self.status.emit({
                "final_update": True,
                "message": "No accounts to process",
            })
            return
        
        # Build list of (broker, account) tuples to process
        login_tasks: List[Tuple[str, dict]] = []
        
        if self.selected_accounts:
            # Login only specific accounts
            target_map = {} # (broker_key, client_id) -> bool
            for broker_key, client_id in self.selected_accounts:
                 target_map[(broker_key, client_id)] = True
            
            for broker, account_list in accounts.items():
                for account in account_list:
                    if (broker, account.get('client_id')) in target_map:
                        login_tasks.append((broker, account))
        else:
            # Standard logic (All or Failed only)
            for broker, account_list in accounts.items():
                for account in account_list:
                    if not self.all_login and account.get('status') == "Logged In":
                        continue
                    login_tasks.append((broker, account))
        
        total = len(login_tasks)
        if total == 0:
            self.status.emit({
                "final_update": True,
                "message": "All accounts already logged in",
            })
            return
        
        self.status.emit({
            "status": True,
            "message": f"Starting login for {total} accounts with {self.max_concurrent} concurrent workers",
            "do_refresh": False,
        })
        
        # Track progress
        completed = 0
        successful = 0
        failed = 0
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async with PlaywrightDriver(headless=self.is_headless) as driver:
            async def process_login(broker: str, account: dict) -> dict:
                """Process a single login with semaphore."""
                nonlocal completed, successful, failed
                
                if self._stop_requested:
                    return {"status": False, "message": "Stopped by user"}
                
                async with semaphore:
                    context = None
                    try:
                        context = await driver.new_context()
                        page = await context.new_page()
                        
                        result = await run_broker_login(page, broker, account)
                        
                        # Update account status
                        if result.get('status'):
                            account['status'] = "Logged In"
                            account['last_login'] = time.strftime("%Y-%m-%d %H:%M:%S")
                            successful += 1
                        else:
                            account['status'] = "Login Failed"
                            failed += 1
                        
                        # Emit individual status
                        self.status.emit({
                            "status": result.get('status', False),
                            "message": f"{account['client_id']}: {result.get('message', 'Unknown')}",
                            "do_refresh": result.get('status', False),
                        })
                        
                        return result
                        
                    except Exception as e:
                        logging.error(f"Login error for {account.get('client_id')}: {e}")
                        account['status'] = "Login Failed"
                        failed += 1
                        return {"status": False, "message": str(e)}
                        
                    finally:
                        if context:
                            try:
                                await context.close()
                            except Exception:
                                pass
                        
                        completed += 1
                        self.progress.emit(completed, total)
            
            # Create tasks for all logins
            tasks = [
                process_login(broker, account)
                for broker, account in login_tasks
            ]
            
            # Run all concurrently (semaphore controls actual parallelism)
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Save updated accounts
        try:
            with open(path, "w") as f:
                json.dump(accounts, f)
        except Exception as e:
            logging.error(f"Failed to save accounts.json: {e}")
        
        # Final status
        self.status.emit({
            "final_update": True,
            "message": f"Completed: {successful} successful, {failed} failed out of {total} accounts",
            "do_refresh": True,
        })


class FailedAccountsExecutorWorker(ExecutorWorker):
    """
    Executor that only processes failed/logged-out accounts.
    """
    
    def __init__(self, data_dir, parent=None, is_headless: bool = True, max_concurrent: int = None):
        super().__init__(
            data_dir=data_dir,
            all_login=False,
            parent=parent,
            is_headless=is_headless,
            max_concurrent=max_concurrent
        )
