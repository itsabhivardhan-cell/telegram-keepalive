import asyncio
import logging
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError, FloodWaitError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("keep_bot_active")

# Parse environment variables safely
API_ID = int(os.environ["API_ID"].strip())
API_HASH = os.environ["API_HASH"].strip().strip("\"'")
SESSION_STRING = os.environ["SESSION_STRING"].strip().strip("\"'")
TARGETS = [b.strip() for b in os.environ.get("BOT_USERNAMES", "").split(",") if b.strip()]
MESSAGE = os.environ.get("MESSAGE", "hi")
LOOP_SECONDS = int(os.environ.get("LOOP_SECONDS", "0"))


def to_target(t):
    if t.lstrip("-").isdigit():  # numeric chat ID (groups/channels)
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

    # Load dialogs so Telethon resolves target entity IDs/usernames accurately
    await client.get_dialogs()

    had_error = await send_all(client)

    # If running continuously as a Render Worker (LOOP_SECONDS > 0)
    while LOOP_SECONDS > 0:
        await asyncio.sleep(LOOP_SECONDS)
        had_error = await send_all(client)

    await client.disconnect()

    # If running as a Cron Job, exit with code 1 if errors occurred
    if had_error and LOOP_SECONDS == 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
