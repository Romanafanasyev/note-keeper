# bot/keyboards/keyboards.py
from aiogram import types


def main_kb() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                types.KeyboardButton(text="➕ Новое событие"),
                types.KeyboardButton(text="📋 Мои планы"),
            ]
        ],
    )
