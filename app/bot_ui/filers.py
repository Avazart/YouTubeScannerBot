import logging
from typing import Union

from aiogram.client.bot import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


class BotAdminFilter(BaseFilter):
    def __init__(self, bot_admin_ids):
        super().__init__()
        self._bot_admin_ids = bot_admin_ids

    async def __call__(
        self,
        mq: Message | CallbackQuery,
        *args,
        **kwargs,
    ) -> bool:
        if mq.from_user:
            return mq.from_user.id in self._bot_admin_ids
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


class TestFilter(BaseFilter):
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
                logger.warning("mq.message is None")
                return False
            chat = mq.message.chat
        logger.debug(f"{chat.type=}, {chat.id=}, {mq.from_user.id=}")

        return True
