"""
app.py - Render-compatible version
------------------------------------
Runs a tiny web server (so Render's free "Web Service" tier accepts it)
while a background thread runs the actual Telegram keep-alive loop,
sending a message every 1 minute exactly - same precision as running
it locally, but hosted in the cloud for free.

An external free pinger (e.g. UptimeRobot, cron-job.org) should hit
this server's URL every ~10 minutes so Render doesn't put it to sleep
after 15 minutes of no incoming HTTP traffic. The ping only keeps the
server AWAKE - it does not control the message timing, which is
handled independently by the background loop below.

ENV VARS (set these in Render's dashboard under your service's
"Environment" tab - NOT hardcoded here):
  API_ID          - your api_id from my.telegram.org
  API_HASH        - your api_hash from my.telegram.org
  SESSION_STRING  - from generate_session.py (run locally once)
  BOT_USERNAMES   - comma-separated, e.g. "bot_one,bot_two"
  MESSAGE         - optional, defaults to "hi"
"""

import asyncio
import logging
import os
import threading

from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("keep_bot_active")

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
BOT_USERNAMES = [b.strip() for b in os.environ["BOT_USERNAMES"].split(",") if b.strip()]
MESSAGE = os.environ.get("MESSAGE", "hi")
INTERVAL_SECONDS = int(os.environ.get("INTERVAL_SECONDS", "60"))

app = Flask(__name__)


@app.route("/")
def health_check():
    # This is what the external pinger (UptimeRobot etc.) hits
    # to keep Render from putting the service to sleep.
    return "Bot keep-alive service is running.", 200


async def ping_bots(client: TelegramClient):
    while True:
        for bot in BOT_USERNAMES:
            username = bot if bot.startswith("@") else f"@{bot}"
            try:
                await client.send_message(username, MESSAGE)
                log.info(f"Sent '{MESSAGE}' to {username}")
            except RPCError as e:
                log.warning(f"Telegram error messaging {username}: {e}")
            except Exception as e:
                log.warning(f"Failed to message {username}: {e}")
        await asyncio.sleep(INTERVAL_SECONDS)


async def telegram_main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    log.info("Logged in. Starting keep-alive loop...")
    try:
        await ping_bots(client)
    finally:
        await client.disconnect()


def run_telegram_loop():
    # Runs the Telegram async loop in its own thread, separate from Flask.
    asyncio.run(telegram_main())


if __name__ == "__main__":
    # Start the Telegram loop in the background, then serve HTTP requests
    # on the main thread so Render sees a responsive web service.
    thread = threading.Thread(target=run_telegram_loop, daemon=True)
    thread.start()

    port = int(os.environ.get("PORT", 10000))  # Render sets PORT automatically
    app.run(host="0.0.0.0", port=port)
