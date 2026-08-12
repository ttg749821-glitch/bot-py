import asyncio
import os
import requests

from telegram.ext import Application


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN ="7920233770:AAHWGQBRMVNXj9SKJE5UgY2ksZQCmcUnH44"

CHANNEL = "@ResultAuto_Bot"

LAST_RESULTS = set()


# ============================================================
# GET NSE RESULTS
# ============================================================

def get_nse_results():

    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }

    try:

        # First visit NSE homepage to establish session/cookies
        session.get(
            "https://www.nseindia.com/",
            headers=headers,
            timeout=20
        )

        url = (
            "https://www.nseindia.com/api/"
            "corporate-announcements?index=equities"
        )

        response = session.get(
            url,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            print("NSE returned unexpected data")
            return []

        results = []

        for item in data:

            subject = str(
                item.get("desc", "")
            ).lower()

            details = str(
                item.get("attchmntText", "")
            ).lower()

            text = subject + " " + details

            if (
                "financial results" in text
                or "integrated filing- financial" in text
                or "integrated filing - financial" in text
                or "quarterly results" in text
                or "quarter ended" in text
            ):
                results.append(item)

        return results

    except Exception as error:

        print("NSE ERROR:", error)

        return []


# ============================================================
# CREATE TELEGRAM MESSAGE
# ============================================================

def make_message(item):

    symbol = str(
        item.get("symbol", "")
    ).strip()

    company = str(
        item.get("sm_name", "")
    ).strip()

    subject = str(
        item.get("desc", "")
    ).strip()

    details = str(
        item.get("attchmntText", "")
    ).strip()

    date_time = str(
        item.get("an_dt", "")
    ).strip()

    pdf = str(
        item.get("attchmntFile", "")
    ).strip()

    message = "📊 QUARTERLY RESULT\n\n"

    if company:
        message += f"🏢 Company: {company}\n"

    if symbol:
        message += f"🔹 NSE Symbol: {symbol}\n"

    if subject:
        message += f"📌 Result Type: {subject}\n"

    if details:
        message += f"📝 Details: {details}\n"

    if date_time:
        message += f"🕐 Date & Time: {date_time}\n"

    if pdf:

        message += (
            "\n📄 ORIGINAL NSE PDF:\n"
            f"{pdf}\n"
        )

    message += (
        "\n🇮🇳 Source: NSE India Official"
    )

    # Telegram message limit
    return message[:4000]


# ============================================================
# CHECK NSE EVERY 60 SECONDS
# ============================================================

async def check_results(application):

    global LAST_RESULTS

    while True:

        try:

            # requests is synchronous, so run it outside
            # the Telegram event loop
            results = await asyncio.to_thread(
                get_nse_results
            )

            print(
                f"NSE CHECK: {len(results)} result(s) found"
            )

            for item in reversed(results):
                unique_id = (
                    str(item.get("seq_id", ""))
                    + str(item.get("symbol",
""))
                    + str(item.get("an_dt", ""))
                    + str(item.get("attchmntFile", ""))
                    + str(item.get("desc", ""))
                )

                if not unique_id:
                    continue

                # Already processed
                if unique_id in LAST_RESULTS:
                    continue

                # On first run, don't send all old NSE results
                if not LAST_RESULTS:
                    LAST_RESULTS.add(unique_id)
                    continue

                message = make_message(item)

                try:

                    await application.bot.send_message(
                        chat_id=CHANNEL,
                        text=message,
                        disable_web_page_preview=False
                    )

                    LAST_RESULTS.add(unique_id)

                    print(
                        "RESULT SENT:",
                        item.get("symbol", "")
                    )

                except Exception as telegram_error:

                    print(
                        "TELEGRAM ERROR:",
                        telegram_error
                    )

            # Keep only the latest 1500 IDs
            LAST_RESULTS = set(
                list(LAST_RESULTS)[-1500:]
            )

        except Exception as error:

            print(
                "AUTOMATIC ERROR:",
                error
            )

        # Check again after 60 seconds
        await asyncio.sleep(60)


# ============================================================
# BOT STARTUP
# ============================================================

async def post_init(application):

    asyncio.create_task(
        check_results(application)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN environment variable "
            "is not set."
        )

    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    print(
        "NSE QUARTERLY RESULT BOT IS RUNNING"
    )

    application.run_polling()

# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    
    main()
    