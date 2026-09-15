
"""Regression test for the startup crash on a malformed last_login.

Reported traceback:

    File "app.py", line 117, in __init__
        self.refresh_accounts_in_table()
    File "app.py", line 769, in refresh_accounts_in_table
        last_login = datetime.strptime(account['last_login'], "%Y-%m-%d %H:%M:%S")
    ValueError: time data '13-07-2026 09:29' does not match format '%Y-%m-%d %H:%M:%S'

Run with: python test_last_login_parsing.py
"""

import ast
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add src to path so we can import the module
current_dir = Path.cwd()
src_dir = current_dir / "src"
sys.path.append(str(src_dir))

from autologin.utils.datetime_utils import (
    CANONICAL_FORMAT,
    normalize_datetime,
    parse_datetime,
)

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


print("=== datetime_utils ===")

# The exact value from the crash report, as a spreadsheet writes it.
check("excel dd-mm-yyyy hh:mm", parse_datetime("13-07-2026 09:29"), datetime(2026, 7, 13, 9, 29))
check("normalize excel value", normalize_datetime("13-07-2026 09:29"), "2026-07-13 09:29:00")

# The format the app itself writes must keep working, unchanged.
check("canonical", parse_datetime("2026-07-13 09:29:00"), datetime(2026, 7, 13, 9, 29))
check("canonical round-trip", normalize_datetime("2026-07-13 09:29:00"), "2026-07-13 09:29:00")

# Other shapes a spreadsheet or pandas emits.
check("slashes dayfirst", parse_datetime("13/07/2026 09:29"), datetime(2026, 7, 13, 9, 29))
check("seconds dayfirst", parse_datetime("13-07-2026 09:29:07"), datetime(2026, 7, 13, 9, 29, 7))
check("iso T", parse_datetime("2026-07-13T09:29:00"), datetime(2026, 7, 13, 9, 29))
check("date only", parse_datetime("2026-07-13"), datetime(2026, 7, 13, 0, 0))
check("surrounding space", parse_datetime("  13-07-2026 09:29  "), datetime(2026, 7, 13, 9, 29))

# Ambiguous dd/mm vs mm/dd resolves day-first, matching an Indian locale.
check("ambiguous dayfirst", parse_datetime("05-07-2026 09:29"), datetime(2026, 7, 5, 9, 29))

# Junk must never raise -- callers rely on None to mark the account logged out.
for junk in ["", None, "   ", "not a date", "nan", "0", 12345]:
    try:
        check(f"junk {junk!r}", parse_datetime(junk), None)
        check(f"junk normalize {junk!r}", normalize_datetime(junk), "")
    except Exception as e:
        failures.append(f"junk {junk!r} raised {type(e).__name__}: {e}")

print(f"checks run, {len(failures)} failure(s) so far")


print("=== _refresh_account_session_state ===")

# app.py cannot be imported without a Qt display, so the method is lifted out
# of the file with ast and run directly. It only needs datetime and the helpers.
app_src = Path(src_dir, "autologin/app.py").read_text()
tree = ast.parse(app_src)
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AutoLogin")
method = next(
    n for n in cls.body
    if isinstance(n, ast.FunctionDef) and n.name == "_refresh_account_session_state"
)
ns = {
    "datetime": datetime,
    "CANONICAL_FORMAT": CANONICAL_FORMAT,
    "normalize_datetime": normalize_datetime,
    "parse_datetime": parse_datetime,
}
exec(compile(ast.Module(body=[method], type_ignores=[]), "app.py", "exec"), ns)
refresh_state = ns["_refresh_account_session_state"]

today = datetime.now().strftime(CANONICAL_FORMAT)


def state(account):
    try:
        changed = refresh_state(None, account)
    except Exception as e:
        failures.append(f"{account}: raised {type(e).__name__}: {e}")
        return None
    return changed


# The reported crash: a spreadsheet-mangled last_login must not raise.
acc = {"client_id": "AB1234", "status": "Logged In",
       "last_login": "13-07-2026 09:29", "added_on": "13-07-2026 09:29"}
if state(acc) is not None:
    check("excel-mangled status", acc["status"], "Logged Out")
    check("excel-mangled last_login", acc["last_login"], "")
    check("excel-mangled added_on", acc["added_on"], "2026-07-13 09:29:00")

# Unparseable junk is expired rather than raised on.
acc = {"client_id": "X1", "status": "Logged In", "last_login": "not a date", "added_on": ""}
if state(acc) is not None:
    check("junk status", acc["status"], "Logged Out")

# Missing keys must not raise -- this used to be a KeyError on 'status'.
state({"client_id": "D1"})

# A session from today survives untouched.
acc = {"client_id": "F1", "status": "Logged In", "last_login": today, "added_on": today}
if state(acc) is not None:
    check("fresh status", acc["status"], "Logged In")
    check("fresh last_login", acc["last_login"], today)

# A same-day login in the mangled format is kept, but rewritten canonically so
# accounts.json heals itself.
acc = {"client_id": "N1", "status": "Logged In",
       "last_login": datetime.now().strftime("%d-%m-%Y %H:%M"), "added_on": ""}
if state(acc) is not None:
    check("heal status", acc["status"], "Logged In")
    check("heal last_login", acc["last_login"], datetime.now().strftime("%Y-%m-%d %H:%M:00"))

# A logged-out account is left alone.
acc = {"client_id": "Z1", "status": "Logged Out", "last_login": "", "added_on": today}
check("logged-out unchanged", state(acc), False)


print("=== refresh_accounts_in_table (end to end) ===")
try:
    import pandas as pd
except ImportError:
    print("pandas not installed, skipping")
else:
    methods = [
        n for n in cls.body
        if isinstance(n, ast.FunctionDef)
        and n.name in ("_refresh_account_session_state", "refresh_accounts_in_table")
    ]
    ns2 = dict(ns, os=os, json=json, pd=pd, logging=logging,
               pandasModel=lambda df, editable=False: df)
    exec(compile(ast.Module(body=methods, type_ignores=[]), "app.py", "exec"), ns2)

    class Stub:
        _refresh_account_session_state = ns2["_refresh_account_session_state"]
        refresh_accounts_in_table = ns2["refresh_accounts_in_table"]

        def __init__(self, data_dir):
            self.data_dir = Path(data_dir)
            self.accounts_df = None
            self.model = None
            self.accounts_table = self

        def setModel(self, m):
            self.model = m

    def run(label, accounts):
        tmp = tempfile.mkdtemp()
        path = Path(tmp, "accounts.json")
        path.write_text(json.dumps(accounts))
        stub = Stub(tmp)
        try:
            stub.refresh_accounts_in_table()
        except Exception as e:
            failures.append(f"{label}: raised {type(e).__name__}: {e}")
            return None, None
        return stub, json.loads(path.read_text())

    stub, saved = run("startup", {
        "zerodha": [{"client_id": "AB1234", "status": "Logged In",
                     "last_login": "13-07-2026 09:29", "added_on": "13-07-2026 09:29"}],
        "upstox": [{"client_id": "X1", "status": "Logged In",
                    "last_login": "not a date", "added_on": ""}],
        "dhan": [{"client_id": "D1"}],
    })
    if stub:
        check("startup zerodha expired", saved["zerodha"][0]["status"], "Logged Out")
        check("startup upstox expired", saved["upstox"][0]["status"], "Logged Out")
        if stub.model is None or len(stub.model) != 3:
            failures.append("startup: table not populated with all 3 rows")

    run("empty", {})


if failures:
    print("\nFAIL")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("\nPASS")
