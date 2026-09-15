"""Tolerant parsing for the timestamps stored in accounts.json.

The app itself always writes ``CANONICAL_FORMAT``, but ``added_on`` and
``last_login`` also arrive through CSV import, where a spreadsheet has usually
rewritten them in the machine's locale format (e.g. ``13-07-2026 09:29``).
Parsing those with a single hard-coded format raised ValueError during startup
and prevented the main window from opening, so every read goes through here.
"""

from datetime import datetime

CANONICAL_FORMAT = "%Y-%m-%d %H:%M:%S"

# Tried in order. Day-first variants come before month-first ones because the
# app targets Indian brokers, where a spreadsheet writes 05/07/2026 as 5 July.
ACCEPTED_FORMATS = (
    CANONICAL_FORMAT,
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%y %H:%M:%S",
    "%d-%m-%y %H:%M",
    "%d/%m/%y %H:%M:%S",
    "%d/%m/%y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
)


def parse_datetime(value):
    """Return a datetime for *value*, or None if it cannot be understood.

    Never raises: callers treat None as "no usable timestamp" and fall back to
    marking the account logged out.
    """
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text or text.lower() in ("nan", "nat", "none", "null"):
        return None

    for fmt in ACCEPTED_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def normalize_datetime(value):
    """Return *value* rewritten in CANONICAL_FORMAT, or "" if unparseable."""
    parsed = parse_datetime(value)
    return parsed.strftime(CANONICAL_FORMAT) if parsed else ""
