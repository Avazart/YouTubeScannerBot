from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from ..bot_types import (
    BotContext,
    Data,
    StorageKey,
    Keyboard,
    NavigationData)
from ..keyboards import (
    build_main_keyboard,
    build_telegram_tg_keyboard
)
from ...settings import MAX_TG_COUNT

router = Router(name=__name__)

async def show_main_keyboard(key: StorageKey,
                             message: Message,
                             bot: Bot,
                             context: BotContext):
    is_owner = key.user_id in context.settings.bot_admin_ids
    keyboard = build_main_keyboard(is_owner)
    m = await message.answer("Main menu:", reply_markup=keyboard)
    if data := await context.storage.get_data(key):
        try:  # try remove keyboard
            if data.keyboard_id is not None:
                await bot.delete_message(message.chat.id, data.keyboard_id)
        except TelegramBadRequest:
            pass

    data = Data(m.message_id,
                original_chat_id=key.chat_id,
                original_thread_id=key.thread_id)
    await context.storage.set_data(key, data)

async def show_tg_keyboard(query: CallbackQuery, context: BotContext):
    if query.message is None:
        return

    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavigationData(keyboard=Keyboard.MAIN).pack()
        data.tgs_offset = 0
        async with context.session_maker.begin() as session:
            keyboard = await build_telegram_tg_keyboard(
                data.tgs_offset,
                MAX_TG_COUNT,
                data.back_callback_data,
                session
            )
            await query.message.edit_text('Telegram chats and threads:')
            await query.message.edit_reply_markup(reply_markup=keyboard)
            await context.storage.set_data(key, data)












