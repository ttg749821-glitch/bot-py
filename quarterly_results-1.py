"""
Cristal MarketIQ - Quarterly Result Monitor
-------------------------------------------
This module checks NSE/BSE corporate announcements for quarterly-result
related filings and can be imported from bot.py.

The function is intentionally lightweight and does not start its own
Telegram polling loop. Your main bot remains responsible for polling.
"""

import hashlib
import re
from typing import Any

import requests


NSE_URL = "https://www.nseindia.com/api/corporate-announcements"
BSE_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"

RESULT_KEYWORDS = (
    "financial results",
    "financial result",
    "quarterly results",
    "quarterly result",
    "unaudited financial results",
    "audited financial results",
    "results for the quarter",
    "results for quarter",
    "standalone financial results",
    "consolidated financial results",
)


def _clean(value: Any) -> str:
    """Convert a value to clean text."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _is_result(text: str) -> bool:
    """Return True when an announcement looks like a quarterly result."""
    text = _clean(text).lower()
    return any(keyword in text for keyword in RESULT_KEYWORDS)


def _item_id(item: dict) -> str:
    """Create a stable ID for de-duplication."""
    raw = "|".join(
        [
            _clean(item.get("symbol")),
            _clean(item.get("scrip_cd")),
            _clean(item.get("company")),
            _clean(item.get("subject")),
            _clean(item.get("dt")),
            _clean(item.get("newsid")),
            _clean(item.get("attchmntFile")),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_nse_quarterly_results() -> list[dict]:
    """Fetch recent NSE corporate announcements matching result keywords."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }

    session = requests.Session()

    try:
        session.get(
            "https://www.nseindia.com/",
            headers=headers,
            timeout=15,
        )

        response = session.get(
            NSE_URL,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    if not isinstance(data, list):
        return []

    results = []

    for item in data:
        if not isinstance(item, dict):
            continue

        text = " ".join(
            [
                _clean(item.get("subject")),
                _clean(item.get("desc")),
                _clean(item.get("attchmntText")),
            ]
        )

        if not _is_result(text):
            continue

        result = {
            "exchange": "NSE",
            "symbol": _clean(item.get("symbol")),
            "company": _clean(item.get("sm_name") or item.get("company")),
            "subject": _clean(item.get("subject") or item.get("desc")),
            "date": _clean(item.get("dt")),
            "pdf": _clean(item.get("attchmntFile")),
        }

        result["id"] = _item_id(result)
        results.append(result)

    return results


def get_bse_quarterly_results() -> list[dict]:
    """
    Fetch BSE result announcements.

    BSE periodically changes its public API parameters. If BSE returns an
    unexpected response, this function safely returns an empty list instead
    of stopping the main Telegram bot.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bseindia.com/",
    }

    params = {
        "pageno": 1,
        "strCat": "Company Update",
        "strPrevDate": "",
        "strToDate": "",
        "strSearch": "",
        "strScrip": "",
        "strType": "C",
        "subcategory": "",
    }

    try:
        response = requests.get(
            BSE_URL,
            params=params,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    rows = []

    if isinstance(data, dict):
        for key in ("Table", "Table1", "data", "results"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
    elif isinstance(data, list):
        rows = data

    results = []

    for item in rows:
        if not isinstance(item, dict):
            continue

        text = " ".join(str(v) for v in item.values())
        if not _is_result(text):
            continue

        result = {
            "exchange": "BSE",
            "symbol": _clean(
                item.get("SCRIP_CD")
                or item.get("scrip_cd")
                or item.get("Scrip_Code")
            ),
            "company": _clean(
                item.get("SLONGNAME")
                or item.get("company")
                or item.get("Company_Name")
            ),
            "subject": _clean(
                item.get("NEWS_SUB")
                or item.get("subject")
                or item.get("Headline")
                or item.get("NEWS_DT")
            ),
            "date": _clean(
                item.get("NEWS_DT")
                or item.get("dt")
                or item.get("Date")
            ),
            "pdf": _clean(
                item.get("ATTACHMENTNAME")
                or item.get("attachment")
                or item.get("PDF")
            ),
        }

        result["id"] = _item_id(result)
        results.append(result)

    return results


def check_quarterly_results(*args, **kwargs) -> list[dict]:
    """
    Check both exchanges and return only new quarterly-result announcements.

    It is safe to call this repeatedly from bot.py. Duplicate announcements
    are filtered during the lifetime of the running process.

    Example:
        results = check_quarterly_results()
    """
    if not hasattr(check_quarterly_results, "_seen"):
        check_quarterly_results._seen = set()

    found = []

    for fetcher in (get_nse_quarterly_results, get_bse_quarterly_results):
        try:
            items = fetcher()
        except Exception:
            items = []

        for item in items:
            item_id = item.get("id")
            if not item_id or item_id in check_quarterly_results._seen:
                continue

            check_quarterly_results._seen.add(item_id)
            found.append(item)

    return found


def format_result_message(result: dict) -> str:
    """Create a clean Telegram-ready message."""
    exchange = _clean(result.get("exchange")) or "EXCHANGE"
    company = _clean(result.get("company")) or "Company"
    symbol = _clean(result.get("symbol"))
    subject = _clean(result.get("subject")) or "Quarterly Result Announcement"
    date = _clean(result.get("date"))
    pdf = _clean(result.get("pdf"))

    title = f"📊 {company}"
    if symbol:
        title += f" ({symbol})"

    lines = [
        "💠 CRISTAL MARKETIQ",
        "",
        title,
        f"🏦 Exchange: {exchange}",
        f"📢 {subject}",
    ]

    if date:
        lines.append(f"📅 Date: {date}")

    if pdf:
        lines.extend(["", f"📄 Result PDF: {pdf}"])

    lines.extend(
        [
            "",
            "🔎 Quarterly Result Announcement detected.",
        ]
    )

    return "\n".join(lines)


async def send_quarterly_results(bot, chat_id: str | int) -> int:
    """
    Optional helper: check for new results and send them to Telegram.

    Returns the number of messages sent.
    """
    results = check_quarterly_results()
    sent = 0

    for result in results:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=format_result_message(result),
                disable_web_page_preview=True,
            )
            sent += 1
        except Exception:
            # Do not crash the main monitoring loop if Telegram has a
            # temporary error.
            continue

    return sent
