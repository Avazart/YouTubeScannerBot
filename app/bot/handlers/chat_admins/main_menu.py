import contextlib
import logging

from aiogram import Router
from aiogram.client.bot import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ...bot_types import Menu
from ...keyboards import build_main_keyboard
from ...state_history import StateHistory

logger = logging.getLogger(__name__)
router = Router(name=__name__)


async def show_main_keyboard(
    message: Message,
    is_owner: bool,
    bot: Bot,
    state: FSMContext,
):
    keyboard = build_main_keyboard(is_owner)
    m = await message.answer("Main menu:", reply_markup=keyboard)

    keyboard_id = await state.get_value("keyboard_id")
    if keyboard_id is not None:
        with contextlib.suppress(TelegramBadRequest):
            await bot.delete_message(message.chat.id, keyboard_id)

    history = StateHistory([Menu.MAIN])
    keyboard_id = m.message_id

    await state.set_state(Menu.MAIN)
    await state.set_data(
        {
            "keyboard_id": keyboard_id,
            "history": history.as_list(),
            "channel_offset": 0,
            "telegram_offset": 0,
            "category_offset": 0,
            "category_selection": [],
            "attach_category_offset": 0,
            "attach_category_selection": [],
        }
    )
