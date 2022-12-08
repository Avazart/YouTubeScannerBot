from typing import Union

from aiogram.client.bot import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery


class BotAdminFilter(BaseFilter):
    def __init__(self, bot_admin_ids):
        super().__init__()
        self._bot_admin_ids = bot_admin_ids

    async def __call__(self, mq: Union[Message, CallbackQuery], *args, **kwargs) -> bool:
        return mq.from_user.id in self._bot_admin_ids


class ChatAdminFilter(BaseFilter):
    def __init__(self, bot_admin_ids):
        super().__init__()
        self._bot_admin_ids = bot_admin_ids

    async def __call__(self, mq: Union[Message, CallbackQuery], bot: Bot) -> bool:
        chat = mq.chat if isinstance(mq, Message) else mq.message.chat
        if chat.type == 'private':
            return True

        if mq.from_user.id in self._bot_admin_ids:
            return True

        chat_admins = await bot.get_chat_administrators(chat.id)
        chat_admin_ids = frozenset((member.user.id for member in chat_admins))

        return mq.from_user.id in chat_admin_ids
