# bot/handlers/auth.py
from aiogram import Router, types, F
from bot.core.config import config

router = Router()

STICKER_ID = "CAACAgIAAxkBAg-aH2hVA_4yrmXiS5b7KYTrVQhC9_HMAAJybgACuzKoSu6w6TV_mTqeNgQ"

@router.message(F.from_user.id != config.USER_ID)
async def secret_response(msg: types.Message):
    """
    Отвечаем только указанному пользователю.
    """
    await msg.answer("Это не для тебя сделано, и не для таких как ты")
    await msg.answer_sticker(STICKER_ID)
