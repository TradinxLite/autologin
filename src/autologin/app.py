"""
Automatically login into your Broker Accounts
"""

import importlib.metadata
import json
import logging
import os
import pandas as pd
import subprocess
import sys
import platform
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QProgressDialog
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtWidgets import QMainWindow, QHeaderView, QMessageBox, QFileDialog
from autologin.dialogs.add_angelone_dialog import AddAngelOneAccountDialog
from autologin.dialogs.add_fivepaisa_dialog import AddFivePaisaAccountDialog
from autologin.dialogs.add_fyers_dialog import AddFyersAccountDialog
from autologin.dialogs.add_kotakneo_dialog import AddKotakNeoAccountDialog
from autologin.dialogs.add_motilal_dialog import AddMotilalOswalAccountDialog
from autologin.dialogs.add_nuvama_dialog import AddNuvamaAccountDialog
from autologin.dialogs.add_upstox_dialog import AddUpstoxAccountDialog
from autologin.dialogs.add_zerodha_dialog import AddZerodhaAccountDialog
from autologin.dialogs.add_sharekhan_dialog import AddSharekhanAccountDialog
from autologin.dialogs.add_jainam_lite_dialog import AddJainamLiteAccountDialog
from autologin.dialogs.add_dhan_dialog import AddDhanAccountDialog
from autologin.dialogs.add_firstock_dialog import AddFirstockAccountDialog
from autologin.dialogs.how_to_add_angelone import HowToAddAngelOneDialog
from autologin.dialogs.how_to_add_dhan import HowToAddDhanDialog
from autologin.dialogs.how_to_add_motilal import HowToAddMotilalOswalDialog
from autologin.dialogs.how_to_add_nuvama import HowToAddNuvamaDialog
from autologin.dialogs.how_to_add_sharekhan import HowToAddSharekhanDialog
from autologin.dialogs.how_to_add_zerodha import HowToAddZerodhaDialog
from autologin.dialogs.how_to_add_upstox import HowToAddUpstoxDialog
from autologin.dialogs.how_to_add_kotak import HowToAddKotakNeoDialog
from autologin.dialogs.how_to_add_fivepaisa import HowToAddFivePaisaDialog
from autologin.utils.alert_box import fail_box_alert, ok_box_alert
from autologin.utils.table_model import pandasModel
from autologin.utils.install_browser import ensure_browser_installed
from autologin.utils.updater import (
    get_current_version, check_for_updates, UpdateChecker
)
from autologin.dialogs.update_dialog import (
    UpdateAvailableDialog, UpdateProgressDialog, NoUpdateDialog
)
from autologin.workers.executor_worker import ExecutorWorker
from autologin.workers.playwright_driver import detect_optimal_concurrency
from datetime import datetime
from pathlib import Path
from platformdirs import user_data_dir

from autologin.dialogs.add_pocketful_dialog import AddPocketfulAccountDialog


def send_data_to_worker(worker_sender, data):
    worker_sender.emit(data)


def get_data_dir():
    return Path(user_data_dir(appname="AutoLogin")) / "data"



class AutoLogin(QMainWindow):
    worker_data_sender = pyqtSignal(dict)
    show_update_dialog_signal = pyqtSignal(str, str, str) # new_version, download_url, release_notes

    def __init__(self):
        super().__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "ui", "main.ui"), self)
        self.setWindowTitle("Auto Login Platform")
        self.data_dir = get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.is_headless = False

        self.showMaximized()

        self.statusbar_text.hide()

        self.add_angelone_btn.clicked.connect(self.add_angel_one_account)
        self.add_zerodha_btn.clicked.connect(self.add_zerodha_account)
        self.add_upstox_btn.clicked.connect(self.add_upstox_account)
        self.add_sharekhan_btn.clicked.connect(self.add_sharekhan_account)
        self.add_motilaloswal_btn.clicked.connect(self.add_motilaloswal_account)
        self.add_nuvama_btn.clicked.connect(self.add_nuvama_account)
        self.add_jainamlite_btn.clicked.connect(self.add_jainam_lite_account)
        self.add_kotakneo_btn.clicked.connect(self.add_kotakneo_account)
        self.add_fivepaisa_btn.clicked.connect(self.add_fivepaisa_account)
        self.add_fyers_btn.clicked.connect(self.add_fyers_account)
        self.add_dhan_btn.clicked.connect(self.add_dhan_account)
        self.add_firstock_btn.clicked.connect(self.add_firstock_account)
        self.add_pocketful_btn.clicked.connect(self.add_pocketful_account)
        self.delete_acc_btn.clicked.connect(self.delete_selected_account)
        self.login_to_fail_btn.clicked.connect(self.login_to_failed_accounts)
        self.login_to_all_btn.clicked.connect(self.start_login_to_all_accounts)
        self.export_acc_button.clicked.connect(self.export_all_to_csv)
        self.import_acc_button.clicked.connect(self.import_acc_from_csv)
        self.background_button.clicked.connect(self.set_headless)
        self.modify_acc_button.clicked.connect(self.modify_selected_account)
        
        # Initialize Log Console immediately to capture startup logs
        # We import here or at top level. Top level is better but clean.
        from autologin.dialogs.log_console import LogConsole
        self.log_console = LogConsole(self)
        logging.info("Application starting... Log Console initialized.")
        
        # Initialize with detected optimal concurrency
        self.max_concurrent = detect_optimal_concurrency()
        
        # Ensure Playwright browser is installed (first-run)
        self.ensure_browser_ready()
        
        self.refresh_accounts_in_table()
        self.table_functions()
        self.load_user_preferences()
        self.setup_menu_bar()

        # Connect update signal
        self.show_update_dialog_signal.connect(self._show_update_dialog)
        
        # Check for updates after UI is ready

        # Check for updates after UI is ready
        QTimer.singleShot(2000, self.check_for_updates_silent)
        
        # Periodic update check (every 60 minutes)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_for_updates_silent)
        self.update_timer.start(60 * 60 * 1000)  # 60 minutes in milliseconds

    def get_preferences_file(self):
        """Get the path to the preferences file"""
        return self.data_dir / "preferences.json"

    def load_user_preferences(self):
        """Load user preferences from storage"""
        try:
            prefs_file = self.get_preferences_file()
            if prefs_file.exists():
                with open(prefs_file, "r") as f:
                    prefs = json.load(f)
                    self.is_headless = prefs.get("background_login", False)
                    self.update_background_button_text()
            else:
                # Default preferences
                self.is_headless = False
                self.save_user_preferences()
        except Exception as e:
            logging.error(f"Failed to load user preferences: {e}")
            self.is_headless = False

    def save_user_preferences(self):
        """Save user preferences to storage"""
        try:
            prefs = {
                "background_login": self.is_headless
            }
            prefs_file = self.get_preferences_file()
            with open(prefs_file, "w") as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save user preferences: {e}")

    def update_background_button_text(self):
        """Update background button text based on is_headless state"""
        if self.is_headless:
            self.background_button.setText("Background Login: ON")
        else:
            self.background_button.setText("Background Login: OFF")
        self.setup_menu_bar()

    def setup_menu_bar(self):
        """Setup menu bar with File menu for directory access"""
        menubar = self.menuBar()
        menubar.clear()  # Clear existing menus to prevent duplicates
        menubar.setNativeMenuBar(True)  # Use native macOS menu bar

        # File menu
        file_menu = menubar.addMenu('&File')
        
        # Open Installation Directory
        open_install_dir_action = file_menu.addAction('Open Installation Directory')
        open_install_dir_action.setStatusTip('Open the application installation directory')
        open_install_dir_action.triggered.connect(self.open_installation_directory)

        # Open Data Directory (accounts.json location)
        open_data_dir_action = file_menu.addAction('Open Data Directory (accounts.json)')
        open_data_dir_action.setStatusTip('Open the directory containing accounts.json file')
        open_data_dir_action.triggered.connect(self.open_data_directory)

        file_menu.addSeparator()

        # Exit
        exit_action = file_menu.addAction('E&xit')
        exit_action.setStatusTip('Exit application')
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu('&Help')

        check_updates_action = help_menu.addAction('Check for Updates...')
        check_updates_action.setStatusTip('Check for application updates')
        check_updates_action.triggered.connect(self.check_for_updates_manual)
        
        # Show Logs
        logs_action = help_menu.addAction('Show Logs')
        logs_action.setStatusTip('Show application logs')
        logs_action.triggered.connect(self.show_log_console)
        
        help_menu.addSeparator()

        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self.show_about_dialog)

    def open_installation_directory(self):
        """Open the application installation directory in file browser"""
        try:
            install_dir = os.path.dirname(os.path.abspath(__file__))
            self._open_directory(install_dir)
            self.statusBar().showMessage(f"Opened: {install_dir}", 3000)
        except Exception as e:
            fail_box_alert("Error", f"Failed to open installation directory:\n{str(e)}")

    def open_data_directory(self):
        """Open the data directory (containing accounts.json) in file browser"""
        try:
            data_dir = str(self.data_dir)
            self._open_directory(data_dir)
            self.statusBar().showMessage(f"Opened: {data_dir}", 3000)
        except Exception as e:
            fail_box_alert("Error", f"Failed to open data directory:\n{str(e)}")

    def _open_directory(self, path):
        """Open a directory in the system's file browser"""
        system_os = platform.system()

        if system_os == "Windows":
            os.startfile(path)
        elif system_os == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux and others
            subprocess.run(["xdg-open", path])

    def show_about_dialog(self):
        """Show about dialog with application information"""
        install_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = str(self.data_dir)

        about_text = f"""
        <h2>Auto Login Platform</h2>
        <p><b>Automatically login into your broker accounts</b></p>
        
        <p><b>Installation Directory:</b><br/>
        <code>{install_dir}</code></p>
        
        <p><b>Data Directory (accounts.json):</b><br/>
        <code>{data_dir}</code></p>
        
        <p><b>Supported Brokers:</b><br/>
        Angel One, Zerodha, Upstox, Fyers, ShareKhan, Motilal Oswal, 
        Nuvama, Jainam Lite, Kotak Neo, 5Paisa, Dhan, Firstock</p>
        
        <p><i>Version: 1.0</i></p>
        """

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("About Auto Login Platform")
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def set_headless(self):
        self.is_headless = not self.is_headless
        self.update_background_button_text()
        self.save_user_preferences()

    def start_login_to_all_accounts(self):
        # Count accounts
        try:
            with open(f"{self.data_dir}/accounts.json", "r") as f:
                accounts = json.load(f)
            total = sum(len(acc_list) for acc_list in accounts.values())
        except:
            total = 0

        if total == 0:
            fail_box_alert("No Accounts", "No accounts found to login. Please add accounts first.")
            return

        reply = QMessageBox.question(
            self,
            'Confirm Login',
            f'Start login process for all {total} account(s)?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.No:
            return

        self.on_login_started()
        self.executor_worker = ExecutorWorker(self.data_dir, is_headless=self.is_headless)
        self.executor_worker.status.connect(self.update_status)
        self.executor_worker.finished.connect(self.on_login_finished) 
        self.executor_worker.start()
    
    def on_login_started(self):
        for b in (self.login_to_all_btn, self.login_to_fail_btn, self.delete_acc_btn,
                  self.modify_acc_button, self.import_acc_button, self.export_acc_button):
            b.setEnabled(False)
        self.statusBar().showMessage("Login process running... Please wait.")

    def on_login_finished(self):
        for b in (self.login_to_all_btn, self.login_to_fail_btn, self.delete_acc_btn,
                  self.modify_acc_button, self.import_acc_button, self.export_acc_button):
            b.setEnabled(True)
        self.statusBar().showMessage("Login process completed", 5000)

    def delete_selected_account(self):
        if self.accounts_table.currentIndex().row() == -1:
            fail_box_alert("Error", "Select an account to delete")
            return

        selected_rows = self.accounts_table.selectionModel().selectedRows()
        if self.accounts_table.model().rowCount() == 0:
            fail_box_alert("Error", "Select an account to delete")
            return

        if len(selected_rows) == 0:
            selected_rows = [self.accounts_table.model().index(i, 0)
                    for i in range(self.accounts_table.model().rowCount())]

        # Confirmation dialog
        count = len(selected_rows)
        reply = QMessageBox.question(
            self,
            'Confirm Deletion',
            f'Are you sure you want to delete {count} account(s)?\n\nThis action cannot be undone.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        if len(selected_rows) >= 0:
            for selected_row in selected_rows:
                account_data = self.accounts_df.iloc[selected_row.row()]
                broker = account_data['broker']
                client_id = account_data['client_id']

                file_available = os.path.exists(f"{self.data_dir}/accounts.json")
                if not file_available:
                    with open(f"{self.data_dir}/accounts.json", "w") as f:
                        json.dump({}, f)
                        return
                with open(f"{self.data_dir}/accounts.json", "r") as f:
                    accounts = json.load(f)
                if broker not in accounts:
                    fail_box_alert("Error", "Broker not found")
                    return
                for account in accounts[broker]:
                    if account['client_id'] == client_id:
                        accounts[broker].remove(account)
                        break
                with open(f"{self.data_dir}/accounts.json", "w") as f:
                    json.dump(accounts, f)
            self.refresh_accounts_in_table()
            ok_box_alert("Success", f"Successfully deleted {count} account(s)")

    def clear_schedules(self):
        print("Clearing schedules...")
        try:
            os.remove("scheduled_jobs/jobs.json")
            print("Cleared all schedules.")
        except FileNotFoundError:
            print("No scheduled jobs file found.")
        except Exception as e:
            print(f"Error clearing schedules: {e}")
        finally:
            self.refresh_accounts_in_table()

    def update_status(self, update):
        if "final_update" in update and update['final_update']:
            ok_box_alert("Success", update["message"])
            self.statusBar().showMessage(update["message"], 5000)
            # Also refresh table on final update
            if update.get('do_refresh'):
                self.refresh_accounts_in_table()
            return
        self.statusBar().showMessage(update["message"], 5000)
        if update.get('do_refresh'):
            self.refresh_accounts_in_table()

    def place_order(self):
        print("Placing order...")
        payload = {
            "action": "place_order",
        }
        send_data_to_worker(self.worker_data_sender, payload)

    def table_functions(self):
        self.accounts_table.horizontalHeader().setStretchLastSection(True)
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.accounts_table.setSortingEnabled(True)

    def import_acc_from_csv(self):
        # Pick file
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Open CSV File", str(Path.home()),
            "CSV Files (*.csv);;All Files (*)", options=options
        )
        if not file_path:
            return

        # Read CSV
        try:
            df = pd.read_csv(file_path, dtype=str).fillna("")
        except Exception as e:
            fail_box_alert("Import Error", f"Could not read CSV:\n{e}")
            return

        # Accept friendly or internal column names
        colmap = {
            "broker":       ["Broker", "broker"],
            "client_id":    ["Client ID", "client_id", "client id", "clientid"],
            "mobile_number":["Mobile Number", "mobile_number", "mobile"],
            "password":     ["Password", "password"],
            "mpin":         ["MPIN", "mpin"],
            "totp_key":     ["TOTP Key", "totp_key", "totp"],
            "api_key":      ["API Key", "api_key"],
            "api_secret":   ["API Secret", "api_secret"],
            "added_on":     ["Added On", "added_on"],
            "last_login":   ["Last Login", "last_login"],
            "status":       ["Status", "status"],
        }
        for target, candidates in colmap.items():
            for c in candidates:
                if c in df.columns:
                    df.rename(columns={c: target}, inplace=True)
                    break

        # Need at least broker + client_id
        if not {"broker", "client_id"}.issubset(df.columns):
            fail_box_alert("Import Error", "CSV must include ‘Broker’ and ‘Client ID’.")
            return

        # Normalize broker names to internal keys
        name_map = {
            "angel one": "angel_one",
            "zerodha": "zerodha",
            "upstox": "upstox",
            "sharekhan": "sharekhan",
            "motilal oswal": "motilal",
            "nuvama": "nuvama",
            "kotakneo": "kotakneo",
            "jainam lite": "jainamlite",
            "fyers": "fyers",
            "5paisa": "fivepaisa",
            "fivepaisa": "fivepaisa",
            "dhan": "dhan",
            "firstock": "firstock",
        }
        def norm_broker(b: str) -> str:
            s = str(b).strip()
            key = s.lower()
            return name_map.get(key, key.replace(" ", "_"))

        df["broker"] = df["broker"].apply(norm_broker)

        # Load existing JSON (or create)
        path = self.data_dir / "accounts.json"
        if path.exists():
            with open(path, "r") as f:
                accounts = json.load(f)
        else:
            accounts = {}

        inserted = updated = skipped = 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Upsert rows
        for _, row in df.iterrows():
            broker = row.get("broker", "").strip()
            client_id = row.get("client_id", "").strip()
            if not broker or not client_id:
                skipped += 1
                continue

            rec = {
                "client_id":     client_id,
                "mobile_number": row.get("mobile_number", ""),
                "password":      row.get("password", ""),
                "mpin":          row.get("mpin", ""),
                "totp_key":      row.get("totp_key", ""),
                "api_key":       row.get("api_key", ""),
                "user_key":      row.get("user_key", ""),
                "api_secret":    row.get("api_secret", ""),
                "added_on":      row.get("added_on", "") or now_str,
                "last_login":    row.get("last_login", ""),
                "status":        row.get("status", "") or "Logged Out",
            }

            accounts.setdefault(broker, [])
            # find existing by client_id
            idx = next((i for i, a in enumerate(accounts[broker]) if a.get("client_id") == client_id), None)

            if idx is None:
                accounts[broker].append(rec)
                inserted += 1
            else:
                # preserve existing added_on if incoming empty
                if not row.get("added_on") and accounts[broker][idx].get("added_on"):
                    rec["added_on"] = accounts[broker][idx]["added_on"]
                # merge (CSV values win if non-empty)
                merged = {**accounts[broker][idx], **{k: v for k, v in rec.items() if v != ""}}
                accounts[broker][idx] = merged
                updated += 1

        # Save + refresh UI
        with open(path, "w") as f:
            json.dump(accounts, f)

        self.refresh_accounts_in_table()
        ok_box_alert("Import Complete",
                    f"Successfully imported accounts:\n\n"
                    f"New: {inserted}\n"
                    f"Updated: {updated}\n"
                    f"Skipped: {skipped}")

    def export_all_to_csv(self):
        # Ensure accounts variable is always defined
        accounts = {}
        json_path = f"{self.data_dir}/accounts.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    accounts = json.load(f) or {}
            except Exception as e:
                logging.error(f"Failed to read accounts.json for export: {e}")
                accounts = {}

        if not accounts:
            # Nothing to export
            self.accounts_df = pd.DataFrame(columns=["broker", "client_id"])
            return

        data = []
        for broker, account_list in accounts.items():
            for account in account_list:
                # Only attempt to parse last_login when present and status is Logged In
                try:
                    if account.get('status') == "Logged In":
                        last_login_raw = account.get('last_login')
                        if last_login_raw:
                            try:
                                last_login_dt = datetime.strptime(last_login_raw, "%Y-%m-%d %H:%M:%S")
                                current_time = datetime.now()
                                if last_login_dt.date() != current_time.date() and last_login_dt.hour >= 5:
                                    account['status'] = "Logged Out"
                                    account['last_login'] = ""
                                    # persist change
                                    try:
                                        with open(json_path, "w") as f:
                                            json.dump(accounts, f)
                                    except Exception as e:
                                        logging.error(f"Failed to write accounts.json while exporting: {e}")
                            except Exception:
                                # Malformed last_login -> mark logged out to avoid crashes
                                account['status'] = "Logged Out"
                                account['last_login'] = ""
                                try:
                                    with open(json_path, "w") as f:
                                        json.dump(accounts, f)
                                except Exception as e:
                                    logging.error(f"Failed to write accounts.json while exporting: {e}")
                except Exception as e:
                    logging.error(f"Unexpected error while preparing export row: {e}")

                data.append({
                    "broker": broker,
                    **account
                })

        df = pd.DataFrame(data)
        if df.empty:
            df = pd.DataFrame(columns=["broker", "client_id"])
        self.accounts_df = df.copy()
        df['broker'] = df['broker'].replace({
            "angel_one": "Angel One",
            "zerodha": "Zerodha",
            "upstox": "Upstox",
            "sharekhan": "Sharekhan",
            "motilal" : "Motilal Oswal",
            "nuvama" : "Nuvama",
            "kotakneo" : "KotakNeo",
            "jainamlite" : "Jainam Lite",
            "fyers" : "Fyers",
            "fivepaisa" : "5Paisa",
            "dhan" : "Dhan",
            "firstock" : "Firstock",
            "pocketful" : "Pocketful",
        })
        df.rename(columns={
            "broker": "Broker",
            "client_id": "Client ID",
            "mobile_number": "Mobile Number",
            "password": "Password",
            "mpin": "MPIN",
            "totp_key": "TOTP Key",
            "api_key": "API Key",
            "api_secret": "API Secret",
            "added_on": "Added On",
            # "user_key" : "User Key",
            "last_login": "Last Login",
            "status": "Status"
        }, inplace=True)
        df = df.fillna("")
        downloads_path = str(Path.home() / "Documents" / "AutoLogin")
        os.makedirs(downloads_path, exist_ok=True)
        csv_file_path = os.path.join(downloads_path, "accounts_export.csv")
        df.to_csv(csv_file_path, index=False)
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save CSV File",
            str(Path.home() / "accounts_export.csv"),
            "CSV Files (*.csv);;All Files (*)",
            options=options
        )
        if file_path:
            df.to_csv(file_path, index=False)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Export Complete")
            msg.setText("CSV file has been successfully saved!")
            msg.setInformativeText(f"Location: {file_path}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    def refresh_accounts_in_table(self):
        accounts = {}
        file_available = os.path.exists(f"{self.data_dir}/accounts.json")
        if not file_available:
            self.accounts_df = pd.DataFrame(columns=["broker", "client_id"])
            with open(f"{self.data_dir}/accounts.json", "w") as f:
                json.dump({}, f)
        else:
            with open(f"{self.data_dir}/accounts.json", "r") as f:
                accounts = json.load(f)
            if not accounts:
                self.accounts_df = pd.DataFrame(columns=["broker", "client_id"])
                return
        data = []
        for broker, account_list in accounts.items():
            for account in account_list:
                if account['status'] == "Logged In":
                    last_login = datetime.strptime(account['last_login'], "%Y-%m-%d %H:%M:%S")
                    current_time = datetime.now()
                    if last_login.date() != current_time.date() and last_login.hour >= 5:
                        account['status'] = "Logged Out"
                        account['last_login'] = ""
                        with open(f"{self.data_dir}/accounts.json", "w") as f:
                            json.dump(accounts, f)

                data.append({
                    "broker": broker,
                    **account
                })
        df = pd.DataFrame(data)
        if df.empty:
            df = pd.DataFrame(columns=["broker", "client_id"])
        self.accounts_df = df.copy()
        df['broker'] = df['broker'].replace({
            "angel_one": "Angel One",
            "zerodha": "Zerodha",
            "upstox": "Upstox",
            "sharekhan": "Sharekhan",
            "motilal" : "Motilal Oswal",
            "nuvama" : "Nuvama",
            "kotakneo" : "KotakNeo",
            "jainamlite" : "Jainam Lite",
            "fyers" : "Fyers",
            "fivepaisa" : "5Paisa",
            "dhan" : "Dhan",
            "firstock" : "Firstock",
            "pocketful" : "Pocketful",
        })
        df.rename(columns={
            "broker": "Broker",
            "client_id": "Client ID",
            "mobile_number": "Mobile Number",
            "password": "Password",
            "mpin": "MPIN",
            "totp_key": "TOTP Key",
            "api_key": "API Key",
            # "user_key": "User Key",
            "api_secret": "API Secret",
            "added_on": "Added On",
            "last_login": "Last Login",
            "status": "Status"
        }, inplace=True)
        df = df.fillna("")
        # df = df.drop("User Key", axis=1)
        self.accounts_table.setModel(pandasModel(df, editable=False))

    def add_angel_one_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddAngelOneDialog() 
            self.how_to_dialog.show()

        angel_one_account_dialog = AddAngelOneAccountDialog(show_how_to_dialog)
        angel_one_account_dialog.show()
        if angel_one_account_dialog.exec_():
            payload = angel_one_account_dialog.get_inputs()
            self.add_to_account_list("angel_one", payload)

    def add_zerodha_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddZerodhaDialog() 
            self.how_to_dialog.show()

        zerodha_account_dialog = AddZerodhaAccountDialog(show_how_to_dialog)
        zerodha_account_dialog.show()
        if zerodha_account_dialog.exec_():
            payload = zerodha_account_dialog.get_inputs()
            self.add_to_account_list("zerodha", payload)

    def add_upstox_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddUpstoxDialog() 
            self.how_to_dialog.show()
        
        upstox_account_dialog = AddUpstoxAccountDialog(show_how_to_dialog)
        upstox_account_dialog.show()
        if upstox_account_dialog.exec_():
            payload = upstox_account_dialog.get_inputs()
            self.add_to_account_list("upstox", payload)

    def add_sharekhan_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddSharekhanDialog() 
            self.how_to_dialog.show()

        sharekhan_account_dialog = AddSharekhanAccountDialog(show_how_to_dialog)
        sharekhan_account_dialog.show()
        if sharekhan_account_dialog.exec_():
            payload = sharekhan_account_dialog.get_inputs()
            self.add_to_account_list("sharekhan", payload)

    def add_nuvama_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddNuvamaDialog()
            self.how_to_dialog.show()

        nuvama_account_dialog = AddNuvamaAccountDialog(show_how_to_dialog)
        nuvama_account_dialog.show()
        if nuvama_account_dialog.exec_():
            payload = nuvama_account_dialog.get_inputs()
            self.add_to_account_list("nuvama", payload)
    
    def add_jainam_lite_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddNuvamaDialog()
            self.how_to_dialog.show()

        jainamlite_account_dialog = AddJainamLiteAccountDialog(show_how_to_dialog)
        jainamlite_account_dialog.show()
        if jainamlite_account_dialog.exec_():
            payload = jainamlite_account_dialog.get_inputs()
            self.add_to_account_list("jainamlite", payload)

    def add_kotakneo_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddKotakNeoDialog()
            self.how_to_dialog.show()

        kotakneo_account_dialog = AddKotakNeoAccountDialog(show_how_to_dialog)
        kotakneo_account_dialog.show()
        if kotakneo_account_dialog.exec_():
            payload = kotakneo_account_dialog.get_inputs()
            self.add_to_account_list("kotakneo", payload)

    def add_fivepaisa_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddFivePaisaDialog()
            self.how_to_dialog.show()

        fivepaisa_account_dialog = AddFivePaisaAccountDialog(show_how_to_dialog)
        fivepaisa_account_dialog.show()
        if fivepaisa_account_dialog.exec_():
            payload = fivepaisa_account_dialog.get_inputs()
            self.add_to_account_list("fivepaisa", payload)

    def add_fyers_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddKotakNeoDialog()
            self.how_to_dialog.show()

        fyers_account_dialog = AddFyersAccountDialog(show_how_to_dialog)
        fyers_account_dialog.show()
        if fyers_account_dialog.exec_():
            payload = fyers_account_dialog.get_inputs()
            self.add_to_account_list("fyers", payload)
    
    def add_motilaloswal_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddMotilalOswalDialog()
            self.how_to_dialog.show()

        motilaloswal_account_dialog = AddMotilalOswalAccountDialog(show_how_to_dialog)
        motilaloswal_account_dialog.show()
        if motilaloswal_account_dialog.exec_():
            payload = motilaloswal_account_dialog.get_inputs()
            self.add_to_account_list("motilal", payload)

    def add_dhan_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddDhanDialog()
            self.how_to_dialog.show()

        dhan_account_dialog = AddDhanAccountDialog(show_how_to_dialog)
        dhan_account_dialog.show()
        if dhan_account_dialog.exec_():
            payload = dhan_account_dialog.get_inputs()
            self.add_to_account_list("dhan", payload)

    def add_firstock_account(self):
        def show_how_to_dialog():
            self.how_to_dialog = HowToAddDhanDialog()
            self.how_to_dialog.show()

        firstock_account_dialog = AddFirstockAccountDialog(show_how_to_dialog)
        firstock_account_dialog.show()
        if firstock_account_dialog.exec_():
            payload = firstock_account_dialog.get_inputs()
            self.add_to_account_list("firstock", payload)

    def add_pocketful_account(self):
        pocketful_account_dialog = AddPocketfulAccountDialog()
        pocketful_account_dialog.show()
        if pocketful_account_dialog.exec_():
            payload = pocketful_account_dialog.get_inputs()
            self.add_to_account_list("pocketful", payload)

    def add_to_account_list(self, broker, data):
        data['added_on'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data['last_login'] = ""
        data['status'] = "Logged Out"
        file_available = os.path.exists(f"{self.data_dir}/accounts.json")
        if not file_available:
            with open(f"{self.data_dir}/accounts.json", "w") as f:
                json.dump({}, f)
        with open(f"{self.data_dir}/accounts.json", "r") as f:
            accounts = json.load(f)
        if broker not in accounts:
            accounts[broker] = []
        accounts[broker].append(data)
        with open(f"{self.data_dir}/accounts.json", "w") as f:
            json.dump(accounts, f)

        self.refresh_accounts_in_table()
    
    def login_to_failed_accounts(self):
        # Count failed/logged out accounts
        try:
            with open(f"{self.data_dir}/accounts.json", "r") as f:
                accounts = json.load(f)
            failed = sum(
                1 for broker_accounts in accounts.values()
                for acc in broker_accounts
                if acc.get('status') in ['Login Failed', 'Logged Out', '']
            )
        except:
            failed = 0

        if failed == 0:
            fail_box_alert("No Failed Accounts", "All accounts are already logged in!")
            return

        reply = QMessageBox.question(
            self,
            'Confirm Login',
            f'Start login process for {failed} failed/logged out account(s)?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.No:
            return

        self.on_login_started()
        self.executor_worker = ExecutorWorker(self.data_dir, all_login=False, is_headless=self.is_headless)
        self.executor_worker.status.connect(self.update_status)
        self.executor_worker.finished.connect(self.on_login_finished) 
        self.executor_worker.start()
        
    def ensure_browser_ready(self):
        """Ensure Playwright browser is installed on first run."""
        progress = QProgressDialog(
            "Setting up browser (first-time only)...",
            None,
            0, 0,
            self
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(1000)  # Show after 1 second
        
        def progress_callback(msg):
            progress.setLabelText(msg)
            QtWidgets.QApplication.processEvents()
        
        try:
            if not ensure_browser_installed(progress_callback):
                fail_box_alert(
                    "Browser Setup Failed",
                    "Failed to set up the browser. Please check your internet connection and try again."
                )
        except Exception as e:
            logging.error(f"Browser setup error: {e}")
        finally:
            progress.close()

    def modify_selected_account(self):
        selected_row = self.accounts_table.currentIndex().row()
        if selected_row == -1:
            fail_box_alert("Error", "Select an account to modify")
            return

        account_data = self.accounts_df.iloc[selected_row]
        broker = account_data["broker"].lower().replace(" ", "_")
        client_id = account_data["client_id"]

        broker_dialog_map = {
            "angel_one": AddAngelOneAccountDialog,
            "zerodha": AddZerodhaAccountDialog,
            "upstox": AddUpstoxAccountDialog,
            "sharekhan": AddSharekhanAccountDialog,
            "nuvama": AddNuvamaAccountDialog,
            "motilal": AddMotilalOswalAccountDialog,
            "jainamlite": AddJainamLiteAccountDialog,
            "kotakneo": AddKotakNeoAccountDialog,
            "fyers" : AddFyersAccountDialog,
            "fivepaisa" : AddFivePaisaAccountDialog,
            "dhan" : AddDhanAccountDialog,
            "firstock" : AddFirstockAccountDialog,
            "pocketful" : AddPocketfulAccountDialog,
        }

        if broker not in broker_dialog_map:
            fail_box_alert("Error", "Unsupported broker")
            return

        def noop(): pass

        if broker == "pocketful":
            dialog = broker_dialog_map[broker]()
        else:
            dialog = broker_dialog_map[broker](noop)
        dialog.set_inputs(account_data.to_dict())

        dialog.show()
        if dialog.exec_():
            updated_data = dialog.get_inputs()
            self.update_account_in_json(broker, client_id, updated_data)

    def update_account_in_json(self, broker, client_id, new_data):
        file_path = self.data_dir / "accounts.json"
        with open(file_path, "r") as f:
            accounts = json.load(f)

        if broker not in accounts:
            fail_box_alert("Error", "Broker not found")
            return

        updated = False
        for i, acc in enumerate(accounts[broker]):
            if acc["client_id"] == client_id:
                new_data["added_on"] = acc["added_on"]
                new_data["last_login"] = acc.get("last_login", "")
                new_data["status"] = acc.get("status", "Logged Out")
                accounts[broker][i] = new_data
                updated = True
                break

        if not updated:
            fail_box_alert("Error", "Account not found")
            return

        with open(file_path, "w") as f:
            json.dump(accounts, f)
        self.refresh_accounts_in_table()
        ok_box_alert("Success", f"{client_id} updated successfully!")

    def check_for_updates_silent(self):
        """
        Check for updates silently. 
        Only show dialog if update is available.
        No status bar messages for 'no update' or 'checking' to avoid spamming.
        """
        def on_update_available(new_version, download_url, release_notes):
            self.show_update_dialog_signal.emit(new_version, download_url, release_notes)
        
        # No-op for no update or error in silent mode
        def on_no_update(): pass
        def on_error(e): pass
        
        self.update_checker = UpdateChecker(
            on_update_available=on_update_available,
            on_no_update=on_no_update,
            on_error=on_error,
            on_checking=None # No checking message
        )
        self.update_checker.check_async()
    
    def check_for_updates_on_startup(self):
        # Kept for backward compatibility if needed, but we used silent for startup too
        self.check_for_updates_silent()

    
    def check_for_updates_manual(self):
        """Check for updates with UI feedback (triggered from menu)."""
        self.statusBar().showMessage("Checking for updates...", 3000)
        
        def on_update_available(new_version, download_url, release_notes):
            QTimer.singleShot(0, lambda: self._show_update_dialog(
                new_version, download_url, release_notes
            ))
        
        def on_no_update():
            QTimer.singleShot(0, lambda: self._show_no_update_dialog())
        
        def on_error(error):
            QTimer.singleShot(0, lambda: fail_box_alert(
                "Update Check Failed", 
                f"Could not check for updates:\n{error}"
            ))
        
        self.update_checker = UpdateChecker(
            on_update_available=on_update_available,
            on_no_update=on_no_update,
            on_error=on_error
        )
        self.update_checker.check_async()

    def show_log_console(self):
        """Show the log console window."""
        if not hasattr(self, 'log_console'):
            from autologin.dialogs.log_console import LogConsole
            self.log_console = LogConsole(self)
        
        self.log_console.show()
        self.log_console.raise_()
        self.log_console.activateWindow()
    
    def _show_update_dialog(self, new_version, download_url, release_notes):
        """Show the update available dialog."""
        current_version = get_current_version()
        
        dialog = UpdateAvailableDialog(
            self,
            current_version,
            new_version,
            release_notes or "",
            download_url  # Pass the download URL to the dialog
        )
        
        if dialog.exec_() and download_url:
            # User wants to download
            self._start_update_download(download_url)
    
    def _show_no_update_dialog(self):
        """Show dialog indicating no update is available."""
        current_version = get_current_version()
        dialog = NoUpdateDialog(self, current_version)
        dialog.exec_()
    
    def _start_update_download(self, download_url):
        """Start downloading the update."""
        progress_dialog = UpdateProgressDialog(self, download_url)
        progress_dialog.start_download()
        
        if progress_dialog.exec_():
            # Update was applied, close the app
            QMessageBox.information(
                self,
                "Restart Required",
                "Please restart the application to complete the update."
            )
            self.close()

def main():
    # Linux desktop environments use an app's .desktop file to integrate the app
    # in to their application menus. The .desktop file of this app will include
    # the StartupWMClass key, set to app's formal name. This helps associate the
    # app's windows to its menu item.
    #
    # For association to work, any windows of the app must have WMCLASS property
    # set to match the value set in app's desktop file. For PySide6, this is set
    # with setApplicationName().

    # Single-instance lock to prevent multiple app instances
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_file_path = data_dir / ".app_lock"
    lock_file = None
    
    # Try to acquire a cross-platform file lock
    try:
        lock_file = open(lock_file_path, 'w')
        if platform.system() == "Windows":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID to help with debugging
        lock_file.write(str(os.getpid()))
        lock_file.flush()
    except (IOError, OSError):
        # Another instance is running - exit silently
        print("Another instance of AutoLogin is already running. Exiting.")
        if lock_file:
            lock_file.close()
        sys.exit(0)

    # Find the name of the module that was used to start the app
    app_module = sys.modules["__main__"].__package__
    # Retrieve the app's metadata
    metadata = importlib.metadata.metadata(app_module)

    QtWidgets.QApplication.setApplicationName(metadata["Formal-Name"])

    app = QtWidgets.QApplication(sys.argv)
    main_window = AutoLogin()
    main_window.show()  # Ensure window is shown
    
    exit_code = app.exec()
    
    # Release the lock on exit
    try:
        if platform.system() == "Windows":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
        lock_file_path.unlink(missing_ok=True)
    except Exception:
        pass
    
    sys.exit(exit_code)

