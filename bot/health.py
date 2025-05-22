import os, sys, asyncio
from aiogram import Bot
from bot.config import BOT_TOKEN

async def main():
    bot = Bot(BOT_TOKEN)
    me = await bot.get_me()
    print(me.username)
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
