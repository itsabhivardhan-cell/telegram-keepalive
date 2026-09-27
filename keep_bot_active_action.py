"""
keep_bot_active_action.py
--------------------------
GitHub Actions version: logs in using a saved session string (from
generate_session.py), sends "hi" to your bot(s) ONCE, then exits.
The GitHub Actions workflow calls this on a schedule (every 5 minutes)
instead of it running in an endless loop.

All secrets (API_ID, API_HASH, SESSION_STRING, BOT_USERNAMES) are read
from environment variables, which the workflow file supplies from
GitHub repo secrets - nothing sensitive is hardcoded here.
"""

import asyncio
import logging
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("keep_bot_active")

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
# Comma-separated list of bot usernames, e.g. "bot_one,bot_two"
BOT_USERNAMES = [b.strip() for b in os.environ["BOT_USERNAMES"].split(",") if b.strip()]
MESSAGE = os.environ.get("MESSAGE", "hi")


async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    log.info("Logged in. Sending messages...")

    had_error = False
    for bot in BOT_USERNAMES:
        username = bot if bot.startswith("@") else f"@{bot}"
        try:
            await client.send_message(username, MESSAGE)
            log.info(f"Sent '{MESSAGE}' to {username}")
        except RPCError as e:
            log.warning(f"Telegram error messaging {username}: {e}")
            had_error = True
        except Exception as e:
            log.warning(f"Failed to message {username}: {e}")
            had_error = True

    await client.disconnect()
    # Exit non-zero if something failed, so GitHub Actions flags the run
    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
