import logging
from typing import Union

from aiogram.client.bot import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.bot_ui.bot_types import BotContext

logger = logging.getLogger(__name__)


class BotAdminFilter(BaseFilter):
    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        mq: Message | CallbackQuery,
        context: BotContext,
    ) -> bool:
        if mq.from_user:
            return mq.from_user.id in context.settings.bot_admin_ids
        return False


class ChatAdminFilter(BaseFilter):
    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        mq: Union[Message, CallbackQuery],
        bot: Bot,
    ) -> bool:
        if isinstance(mq, Message):
            chat = mq.chat
        else:
            if not mq.message:
                return False
            chat = mq.message.chat

        chat_admins = await bot.get_chat_administrators(chat.id)
        chat_admin_ids = frozenset((member.user.id for member in chat_admins))
        assert mq.from_user
        return mq.from_user.id in chat_admin_ids


class PrivateChatFilter(BaseFilter):
    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        mq: Union[Message, CallbackQuery],
        bot: Bot,
    ) -> bool:
        if isinstance(mq, Message):
            chat = mq.chat
        else:
            if not mq.message:
                return False
            chat = mq.message.chat

        return chat.type == "private"
