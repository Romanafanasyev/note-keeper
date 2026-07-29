# bot/main.py
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command

from bot.core.config import config
from bot.core.db import init_db
from bot.handlers.add import router as add_router
from bot.handlers.edit import router as edit_router
from bot.handlers.list import router as list_router
from bot.keyboards.keyboards import main_kb
from bot.middlewares import AccessControlMiddleware
from bot.scheduler.scheduler import setup_scheduler
from bot.services.updater import update_posts
from bot.utils.logger import logger

dp = Dispatcher()
dp.update.outer_middleware(AccessControlMiddleware(config.USER_ID))
dp.include_router(edit_router)
dp.include_router(list_router)
dp.include_router(add_router)


@dp.message(Command("start", "help"))
async def cmd_start(msg: types.Message):
    logger.info(f"User {msg.from_user.id} issued /start")
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[types.KeyboardButton(text="➕ Новое событие")]],
    )
    await msg.answer("Готов записывать планы.", reply_markup=kb)


@dp.message(Command("force_update"))
async def force_update(msg: types.Message):
    logger.info("Force update triggered")
    await update_posts(msg.bot)
    await msg.answer("Канал обновлён.", reply_markup=main_kb())


async def main():
    logger.info("Starting bot...")
    init_db()
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    scheduler = setup_scheduler(bot)
    try:
        logger.info("Polling started.")
        await dp.start_polling(bot, close_bot_session=False)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logger.exception("Bot crashed")
