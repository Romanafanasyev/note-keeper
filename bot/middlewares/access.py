import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Update

DENIED_TEXT = "Это не для тебя сделано, и не для таких как ты"
PRIVATE_CHAT_TEXT = "Напиши мне в личный чат."
STICKER_ID = "CAACAgIAAxkBAg-aH2hVA_4yrmXiS5b7KYTrVQhC9_HMAAJybgACuzKoSu6w6TV_mTqeNgQ"
MESSAGE_FIELDS = (
    "message",
    "edited_message",
    "business_message",
    "edited_business_message",
    "guest_message",
)
USER_EVENT_FIELDS = (
    *MESSAGE_FIELDS,
    "callback_query",
    "inline_query",
    "chosen_inline_result",
    "shipping_query",
    "pre_checkout_query",
    "purchased_paid_media",
    "poll_answer",
    "message_reaction",
    "business_connection",
    "my_chat_member",
    "chat_member",
    "chat_join_request",
)


class AccessControlMiddleware(BaseMiddleware):
    """Allow interactive updates only from the configured owner in private chat."""

    def __init__(self, owner_id: int, denied_reply_cooldown: float = 60.0) -> None:
        self.owner_id = owner_id
        self.denied_reply_cooldown = denied_reply_cooldown
        self._last_denied_reply: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        user_id = self._user_id(event)
        if user_id is None:
            return None

        if user_id == self.owner_id:
            if self._is_private_interaction(event):
                return await handler(event, data)
            await self._reject_owner_outside_private_chat(event)
            return None

        await self._reject_unauthorized(event, user_id)
        return None

    @staticmethod
    def _user_id(event: Update) -> int | None:
        for field in USER_EVENT_FIELDS:
            candidate = getattr(event, field, None)
            user = getattr(candidate, "from_user", None) or getattr(
                candidate, "user", None
            )
            if user is not None:
                return user.id
        return None

    @staticmethod
    def _is_private_interaction(event: Update) -> bool:
        message = AccessControlMiddleware._message(event)
        if message is not None:
            return message.chat.type == ChatType.PRIVATE

        callback = event.callback_query
        if callback is not None:
            callback_message = callback.message
            chat = getattr(callback_message, "chat", None)
            return chat is not None and chat.type == ChatType.PRIVATE

        return False

    async def _reject_owner_outside_private_chat(self, event: Update) -> None:
        message = self._message(event)
        try:
            if message is not None:
                await message.answer(PRIVATE_CHAT_TEXT)
            elif event.callback_query is not None:
                await event.callback_query.answer(PRIVATE_CHAT_TEXT, show_alert=True)
        except TelegramAPIError:
            return

    async def _reject_unauthorized(self, event: Update, user_id: int) -> None:
        callback = event.callback_query
        if callback is not None:
            try:
                await callback.answer(DENIED_TEXT, show_alert=True)
            except TelegramAPIError:
                pass

        if not self._should_send_denied_reply(user_id):
            return

        message = self._message(event)
        if message is None and callback is not None:
            callback_message = callback.message
            if hasattr(callback_message, "answer"):
                message = callback_message
        if message is None:
            return

        try:
            await message.answer(DENIED_TEXT)
            await message.answer_sticker(STICKER_ID)
        except TelegramAPIError:
            return

    def _should_send_denied_reply(self, user_id: int) -> bool:
        now = time.monotonic()
        last_reply = self._last_denied_reply.get(user_id)
        if last_reply is not None and now - last_reply < self.denied_reply_cooldown:
            return False

        self._last_denied_reply[user_id] = now
        if len(self._last_denied_reply) > 1_000:
            cutoff = now - self.denied_reply_cooldown
            self._last_denied_reply = {
                key: value
                for key, value in self._last_denied_reply.items()
                if value >= cutoff
            }
        return True

    @staticmethod
    def _message(event: Update):
        for field in MESSAGE_FIELDS:
            message = getattr(event, field, None)
            if message is not None:
                return message
        return None
