import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ....constants import MAX_CATEGORY_COUNT, MAX_TG_COUNT
from ...bot_types import BotContext, Menu, PageData, TelegramsMenuData, TgData
from ...keyboards import (
    build_category_filter_keyboard,
    build_telegram_tg_keyboard,
)
from ...state_history import StateHistory

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.callback_query(
    Menu.MAIN,
    TelegramsMenuData.filter(),
    F.message.as_("message"),
)
async def show_telegrams_menu(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    context: BotContext,
):
    data = await state.get_data()
    history = StateHistory.from_list(data["history"])
    telegram_offset = data["telegram_offset"]

    async with context.session_maker.begin() as session:
        keyboard = await build_telegram_tg_keyboard(
            telegram_offset,
            MAX_TG_COUNT,
            session,
        )
        await message.edit_text(
            "Telegram chats and threads:",
            reply_markup=keyboard,
        )

    history.append(Menu.TELEGRAMS)
    await state.update_data({"history": history.as_list()})
    await state.set_state(Menu.TELEGRAMS)


@router.callback_query(
    Menu.TELEGRAMS, TgData.filter(), F.message.as_("message")
)
async def yt_channels_in_tg_pressed(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    callback_data: TgData,
    context: BotContext,
):
    data = await state.get_data()
    history = StateHistory.from_list(data["history"])
    category_offset = data["category_offset"]
    category_selection = data["category_selection"]

    chat_id = callback_data.chat_id
    thread_id = callback_data.thread_id

    async with context.session_maker.begin() as session:
        keyboard = await build_category_filter_keyboard(
            category_offset,
            MAX_CATEGORY_COUNT,
            category_selection,
            session,
        )
        await message.edit_text("YouTube channels:", reply_markup=keyboard)

    await state.update_data(
        {
            "history": history.as_list(),
            "chat_id": chat_id,
            "thread_id": thread_id,
        }
    )
    history.append(Menu.CATEGORIES)
    await state.set_data(Menu.CATEGORIES)


@router.callback_query(
    Menu.TELEGRAMS,
    PageData.filter(),
    F.message.as_("message"),
)
async def paginate_telegrams(
    _query: CallbackQuery,
    message: Message,
    callback_data: PageData,
    state: FSMContext,
    context: BotContext,
):
    telegram_offset = callback_data.offset

    async with context.session_maker.begin() as session:
        keyboard = await build_telegram_tg_keyboard(
            telegram_offset,
            MAX_TG_COUNT,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)

    await state.update_data({"telegram_offset": telegram_offset})
