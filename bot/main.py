# bot/main.py
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command
from bot.core.config import BOT_TOKEN
from bot.keyboards.keyboards import main_kb
from bot.handlers.add import router as add_router
from bot.core.db import init_db
from bot.services.updater import update_posts
from bot.scheduler.scheduler import setup_scheduler
from bot.handlers.list import router as list_router
from bot.handlers.edit import router as edit_router

# --- инициализация ---
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()
dp.include_router(edit_router)
dp.include_router(list_router)
dp.include_router(add_router)

# --- /start & /help ---
@dp.message(Command("start", "help"))
async def cmd_start(msg: types.Message):
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[types.KeyboardButton(text="➕ Новое событие")]]
    )
    await msg.answer("Готов записывать планы.", reply_markup=kb)


@dp.message(Command("force_update"))
async def force_update(msg: types.Message):
    await update_posts(bot)
    await msg.answer("Канал обновлён.", reply_markup=main_kb())

# --- точка входа ---
async def main():
    init_db()
    setup_scheduler(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
