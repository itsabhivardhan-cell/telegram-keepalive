import asyncio
import logging
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError, FloodWaitError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("keep_bot_active")

API_ID = int(os.environ["API_ID"].strip())
API_HASH = os.environ["API_HASH"].strip()
SESSION_STRING = os.environ["SESSION_STRING"].strip()
TARGETS = [b.strip() for b in os.environ["BOT_USERNAMES"].split(",") if b.strip()]
MESSAGE = os.environ.get("MESSAGE", "hi")
# Set LOOP_SECONDS=300 on Render if this is a Worker; leave unset for Cron Job
LOOP_SECONDS = int(os.environ.get("LOOP_SECONDS", "0"))


def to_target(t):
    if t.lstrip("-").isdigit():          # numeric chat ID (groups)
        return int(t)
    return t if t.startswith("@") else f"@{t}"


async def send_all(client):
    had_error = False
    for t in TARGETS:
        target = to_target(t)
        try:
            await client.send_message(target, MESSAGE)
            log.info(f"Sent '{MESSAGE}' to {target}")
        except FloodWaitError as e:
            log.warning(f"FloodWait {e.seconds}s for {target}")
            had_error = True
        except RPCError as e:
            log.warning(f"Telegram error messaging {target}: {type(e).__name__}: {e}")
            had_error = True
        except Exception as e:
            log.warning(f"Failed to message {target}: {type(e).__name__}: {e}")
            had_error = True
    return had_error


async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log.error("SESSION NOT AUTHORIZED. Regenerate SESSION_STRING using the SAME API_ID and API_HASH.")
        await client.disconnect()
        sys.exit(1)

    me = await client.get_me()
    log.info(f"Logged in as {me.first_name} (@{me.username}) id={me.id}")

    # Loads your dialogs so Telethon can resolve groups the account is in
    await client.get_dialogs()

    had_error = await send_all(client)
    while LOOP_SECONDS:
        await asyncio.sleep(LOOP_SECONDS)
        had_error = await send_all(client)

    await client.disconnect()
    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
