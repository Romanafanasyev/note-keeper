import asyncio
import sys

from aiogram import Bot

from bot.core.config import config


async def main():
    bot = Bot(config.BOT_TOKEN.get_secret_value())
    try:
        me = await asyncio.wait_for(bot.get_me(), timeout=10)
        if me.id <= 0:
            raise RuntimeError("Telegram returned an invalid bot identity")
        print("ok")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
