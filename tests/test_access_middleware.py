import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.middlewares.access import (
    DENIED_TEXT,
    PRIVATE_CHAT_TEXT,
    AccessControlMiddleware,
)


def make_update(*, user_id: int, chat_type: str = "private"):
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(type=chat_type),
        answer=AsyncMock(),
        answer_sticker=AsyncMock(),
    )
    update = SimpleNamespace(
        message=message,
        edited_message=None,
        callback_query=None,
        inline_query=None,
        chosen_inline_result=None,
        shipping_query=None,
        pre_checkout_query=None,
        my_chat_member=None,
        chat_member=None,
        chat_join_request=None,
    )
    return update, message


def test_owner_is_allowed_in_private_chat():
    middleware = AccessControlMiddleware(owner_id=42)
    update, message = make_update(user_id=42)
    handler = AsyncMock(return_value="handled")

    result = asyncio.run(middleware(handler, update, {}))

    assert result == "handled"
    handler.assert_awaited_once_with(update, {})
    message.answer.assert_not_awaited()


def test_owner_is_rejected_outside_private_chat():
    middleware = AccessControlMiddleware(owner_id=42)
    update, message = make_update(user_id=42, chat_type="group")
    handler = AsyncMock()

    asyncio.run(middleware(handler, update, {}))

    handler.assert_not_awaited()
    message.answer.assert_awaited_once_with(PRIVATE_CHAT_TEXT)


def test_unknown_user_gets_funny_response_once_per_cooldown():
    middleware = AccessControlMiddleware(owner_id=42, denied_reply_cooldown=60)
    update, message = make_update(user_id=7)
    handler = AsyncMock()

    asyncio.run(middleware(handler, update, {}))
    asyncio.run(middleware(handler, update, {}))

    handler.assert_not_awaited()
    message.answer.assert_awaited_once_with(DENIED_TEXT)
    message.answer_sticker.assert_awaited_once()


def test_owner_callback_is_allowed_in_private_chat():
    middleware = AccessControlMiddleware(owner_id=42)
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(chat=SimpleNamespace(type="private")),
    )
    update, _ = make_update(user_id=0)
    update.message = None
    update.callback_query = callback
    handler = AsyncMock(return_value="handled")

    result = asyncio.run(middleware(handler, update, {}))

    assert result == "handled"
    handler.assert_awaited_once_with(update, {})
