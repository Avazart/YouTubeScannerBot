import logging

from aiogram import F, Router
from aiogram.client.bot import Bot, User
from aiogram.filters import (
    JOIN_TRANSITION,
    ChatMemberUpdatedFilter,
    Command,
)
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Chat, ChatMemberUpdated, Message

from ....auxiliary_utils import get_thread_id
from ....constants import BOT_DESCRIPTION
from ....database.models import TelegramChat, TelegramThread
from ....database.utils import get_destinations
from ...bot_types import (
    BackData,
    BotContext,
    CloseData,
    Menu,
    Status,
)
from ...state_history import StateHistory
from .category_menu import show_categories_menu
from .channel_menu import show_channels_menu
from .main_menu import show_main_keyboard
from .telegrams_menu import show_telegrams_menu

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION)
)
async def bot_added(event: ChatMemberUpdated, context: BotContext):
    logger.info("Bot has been added as a member in chat #%d", event.chat.id)
    async with context.session_maker.begin() as session:
        chat = TelegramChat.from_aiogram_chat(event.chat)
        await session.merge(chat)


@router.message(Command(commands=["start", "help"]))
async def start_command(message: Message):
    logger.debug("chat.type=%s", message.chat.type)
    await message.answer(BOT_DESCRIPTION)


@router.message(Command(commands=["menu"]), F.from_user.as_("from_user"))
async def menu_command(
    message: Message,
    from_user: User,
    state: FSMContext,
    bot: Bot,
    context: BotContext,
):
    async with context.session_maker.begin() as session:
        thread_original_id = get_thread_id(message)
        if tg := await get_destinations(
            message.chat.id,
            thread_original_id,
            session,
        ):
            chat = tg.chat
            if chat.status == Status.BAN:
                return
            chat.status = Status.ON
        else:
            chat = TelegramChat.from_aiogram_chat(message.chat)
        await session.merge(chat)

        if thread_original_id is not None:
            thread = TelegramThread(
                id=tg.get_thread_id() if tg else None,
                original_id=thread_original_id,
                original_chat_id=message.chat.id,
            )
            await session.merge(thread)
    is_owner = from_user.id in context.settings.bot.admin_ids
    await show_main_keyboard(message, is_owner, bot, state)


@router.callback_query(
    BackData.filter(),
    F.message.as_("message"),
    F.message.chat.as_("chat"),
    F.from_user.as_("from_user"),
)
async def handle_back(
    query: CallbackQuery,
    state: FSMContext,
    message: Message,
    from_user: User,
    chat: Chat,
    bot: Bot,
    context: BotContext,
):
    history = StateHistory.from_list(await state.get_value("history"))
    _current_state = history.pop()
    prev_state = history.back()
    await state.update_data({"history": history.as_list()})

    if not prev_state:
        logger.warning("Wrong history!")
        return

    match prev_state:
        case Menu.MAIN:
            is_owner = from_user.id in context.settings.bot.admin_ids
            await show_main_keyboard(message, is_owner, bot, state)
        case Menu.TELEGRAMS:
            await show_telegrams_menu(query, state, message, chat, context)
        case Menu.CATEGORIES:
            await show_categories_menu(query, state, message, chat, context)
        case Menu.ATTACH_CATEGORIES:
            await show_channels_menu(query, state, message, from_user, context)


@router.callback_query(CloseData.filter(), F.message.as_("message"))
async def handle_close(_query: CallbackQuery, message: Message):
    await message.delete()
