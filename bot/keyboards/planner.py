import calendar
import datetime as dt

from aiogram import types

from bot.utils.presentation import MONTHS_NOMINATIVE, task_button_text

WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def cancel_kb(prefix: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"{prefix}:cancel",
                )
            ]
        ]
    )


def date_shortcuts_kb(prefix: str, today: dt.date) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Сегодня",
                    callback_data=f"{prefix}:date:pick:{today.isoformat()}",
                ),
                types.InlineKeyboardButton(
                    text="Завтра",
                    callback_data=(
                        f"{prefix}:date:pick:"
                        f"{(today + dt.timedelta(days=1)).isoformat()}"
                    ),
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="📅 Выбрать дату",
                    callback_data=f"{prefix}:date:nav:{today:%Y-%m}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"{prefix}:cancel",
                )
            ],
        ]
    )


def calendar_kb(
    prefix: str,
    year: int,
    month: int,
) -> types.InlineKeyboardMarkup:
    shown = dt.date(year, month, 1)
    previous = (shown - dt.timedelta(days=1)).replace(day=1)
    following = (shown + dt.timedelta(days=32)).replace(day=1)
    rows = [
        [
            types.InlineKeyboardButton(
                text=f"{MONTHS_NOMINATIVE[month - 1].capitalize()} {year}",
                callback_data="noop",
            )
        ],
        [
            types.InlineKeyboardButton(text=name, callback_data="noop")
            for name in WEEKDAYS
        ],
    ]

    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=str(day) if day else " ",
                    callback_data=(
                        f"{prefix}:date:pick:{year:04d}-{month:02d}-{day:02d}"
                        if day
                        else "noop"
                    ),
                )
                for day in week
            ]
        )

    rows.extend(
        [
            [
                types.InlineKeyboardButton(
                    text="←",
                    callback_data=f"{prefix}:date:nav:{previous:%Y-%m}",
                ),
                types.InlineKeyboardButton(
                    text="К выбору",
                    callback_data=f"{prefix}:date:shortcuts",
                ),
                types.InlineKeyboardButton(
                    text="→",
                    callback_data=f"{prefix}:date:nav:{following:%Y-%m}",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"{prefix}:cancel",
                )
            ],
        ]
    )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def time_kb(prefix: str, *, back_callback: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Весь день",
                    callback_data=f"{prefix}:time:all",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=value,
                    callback_data=f"{prefix}:time:{value}",
                )
                for value in ("09:00", "12:00", "18:00")
            ],
            [
                types.InlineKeyboardButton(
                    text="⌨️ Другое время",
                    callback_data=f"{prefix}:time:custom",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="← Назад",
                    callback_data=back_callback,
                ),
                types.InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"{prefix}:cancel",
                ),
            ],
        ]
    )


def task_actions_kb(
    task_id: int,
    *,
    list_filter: str = "all",
    page: int = 0,
) -> types.InlineKeyboardMarkup:
    suffix = f"{task_id}:{list_filter}:{page}"
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✏️ Название",
                    callback_data=f"task:title:{suffix}",
                ),
                types.InlineKeyboardButton(
                    text="📅 Дата",
                    callback_data=f"task:date:{suffix}",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="🕐 Время",
                    callback_data=f"task:time:{suffix}",
                ),
                types.InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"task:delete:{suffix}",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="← К списку",
                    callback_data=f"list:{list_filter}:{page}",
                )
            ],
        ]
    )


def task_rows(tasks, list_filter: str, page: int):
    return [
        [
            types.InlineKeyboardButton(
                text=task_button_text(task),
                callback_data=f"task:view:{task.id}:{list_filter}:{page}",
            )
        ]
        for task in tasks
    ]
