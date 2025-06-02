import contextlib
import logging

from aiogram import F, Router
from aiogram.client.bot import Bot, User
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import (
    JOIN_TRANSITION,
    ChatMemberUpdatedFilter,
    Command,
    or_f,
)
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from ...auxiliary_utils import get_thread_id
from ...constants import MAX_CATEGORY_COUNT, MAX_TG_COUNT, MAX_YT_CHANNEL_COUNT
from ...database.models import TelegramChat, TelegramThread
from ...database.utils import (
    add_forwarding,
    delete_forwarding,
    get_destinations,
)
from .. import schemas
from ..bot_types import (
    BackData,
    BotContext,
    ChannelsMenuData,
    CloseData,
    History,
    Menu,
    Status,
    TelegramsMenuData,
    TgData,
)
from ..keyboards import (
    CategoriesMenuData,
    CategoryData,
    ChannelData,
    PageData,
    build_attach_categories_keyboard,
    build_category_filter_keyboard,
    build_channel_keyboard,
    build_main_keyboard,
    build_telegram_tg_keyboard,
)

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
    await message.answer(
        "I periodically scan YouTube channels "
        "for new videos and send you links to them in Telegram\n\n"
        "You can control me by sending these commands:\n\n"
        "/menu - open the menu\n\n"
        "/add_channel <url> - add youtube channel"
    )


@router.message(Command(commands=["menu"]))
async def menu_command(
    message: Message,
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
    is_owner = message.from_user.id in context.settings.bot.admin_ids
    await show_main_keyboard(message, is_owner, bot, state)


async def show_main_keyboard(
    message: Message,
    is_owner: bool,
    bot: Bot,
    state: FSMContext,
):
    keyboard = build_main_keyboard(is_owner)
    m = await message.answer("Main menu:", reply_markup=keyboard)

    data = schemas.StateData(**(await state.get_data()))
    if data.keyboard_id is not None:
        with contextlib.suppress(TelegramBadRequest):
            await bot.delete_message(message.chat.id, data.keyboard_id)

    data = schemas.StateData()
    data.history = History([Menu.MAIN.state])
    data.keyboard_id = m.message_id

    await state.set_state(Menu.MAIN)
    await state.set_data(data.model_dump())


@router.callback_query(
    or_f(Menu.MAIN, Menu.TELEGRAMS),
    CategoriesMenuData.filter(),
    F.message.as_("message"),
)
async def show_categories_menu(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    context: BotContext,
):
    data = schemas.StateData(**(await state.get_data()))
    data.history.append(Menu.CATEGORIES.state)

    async with context.session_maker.begin() as session:
        keyboard = await build_category_filter_keyboard(
            data.categories_menu_offset,
            MAX_CATEGORY_COUNT,
            data.selected_categories,
            session,
        )
        await message.edit_text(
            "Select categories for filter youtube channels:",
            reply_markup=keyboard,
        )

    await state.set_state(Menu.CATEGORIES)
    await state.set_data(data.model_dump())


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
    data = schemas.StateData(**(await state.get_data()))
    data.history.append(Menu.TELEGRAMS.state)

    async with context.session_maker.begin() as session:
        keyboard = await build_telegram_tg_keyboard(
            data.telegrams_menu_offset,
            MAX_TG_COUNT,
            session,
        )
        await message.edit_text(
            "Telegram chats and threads:",
            reply_markup=keyboard,
        )

    await state.set_state(Menu.TELEGRAMS)
    await state.set_data(data.model_dump())


@router.callback_query(
    Menu.CATEGORIES,
    ChannelsMenuData.filter(),
    F.message.as_("message"),
    F.from_user.as_("from_user"),
)
async def show_channels_menu(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    from_user: User,
    context: BotContext,
):
    data = schemas.StateData(**(await state.get_data()))
    data.history.append(Menu.CHANNELS.state)

    if len(data.history) < 3:
        logger.warning("History is empty!")
        return

    from_state = data.history[-3]
    match from_state:
        case Menu.MAIN.state:
            data.chat_id = message.chat.id
            data.thread_id = message.message_thread_id
        case Menu.TELEGRAMS.state:
            assert data.chat_id is not None
        case _:
            logger.warning('State "%s" is wrong!', from_state)
            return

    async with context.session_maker.begin() as session:
        keyboard = await build_channel_keyboard(
            data.chat_id,
            data.thread_id,
            from_user.id in context.settings.bot.admin_ids,
            data.channels_menu_offset,
            MAX_YT_CHANNEL_COUNT,
            data.selected_categories,
            session,
        )
        await message.edit_text("YouTube channels:", reply_markup=keyboard)

    await state.set_state(Menu.CHANNELS)
    await state.set_data(data.model_dump())


@router.callback_query(
    PageData.filter(), F.message.as_("message"), F.from_user.as_("from_user")
)
async def navigate(
    _query: CallbackQuery,
    message: Message,
    from_user: User,
    callback_data: PageData,
    state: FSMContext,
    context: BotContext,
):
    data = schemas.StateData(**(await state.get_data()))
    async with context.session_maker.begin() as session:
        match await state.get_state():
            case Menu.TELEGRAMS:
                data.telegrams_menu_offset = callback_data.offset
                keyboard = await build_telegram_tg_keyboard(
                    data.telegrams_menu_offset,
                    MAX_TG_COUNT,
                    session,
                )
            case Menu.CHANNELS:
                data.channels_menu_offset = callback_data.offset
                assert data.chat_id is not None
                keyboard = await build_channel_keyboard(
                    data.chat_id,
                    data.thread_id,
                    from_user.id in context.settings.bot.admin_ids,
                    data.channels_menu_offset,
                    MAX_YT_CHANNEL_COUNT,
                    data.selected_categories,
                    session,
                )
            case Menu.CATEGORIES:
                data.categories_menu_offset = callback_data.offset
                keyboard = await build_category_filter_keyboard(
                    data.categories_menu_offset,
                    MAX_CATEGORY_COUNT,
                    data.categories_ids,
                    session,
                )
            case Menu.ATTACH_CATEGORIES:
                data.categories_offset = callback_data.offset
                assert data.channel_id is not None
                keyboard = await build_attach_categories_keyboard(
                    data.channel_id,
                    data.categories_menu_offset,
                    MAX_CATEGORY_COUNT,
                    session,
                )
        await message.edit_reply_markup(reply_markup=keyboard)
        await state.set_data(data.model_dump())


@router.callback_query(CategoryData.filter(), F.message.as_("message"))
async def category_button_pressed(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    callback_data: CategoryData,
    context: BotContext,
):
    data = schemas.StateData(**(await state.get_data()))
    async with context.session_maker.begin() as session:
        data.selected_categories ^= {callback_data.id}
        keyboard = await build_category_filter_keyboard(
            data.categories_menu_offset,
            MAX_CATEGORY_COUNT,
            data.selected_categories,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)
    await state.set_data(data.model_dump())


@router.callback_query(
    Menu.CHANNELS,
    ChannelData.filter(),
    F.message.as_("message"),
    F.from_user.as_("from_user"),
)
async def channel_checked(
    _query: CallbackQuery,
    message: Message,
    from_user: User,
    callback_data: ChannelData,
    context: BotContext,
    state: FSMContext,
):
    data = schemas.StateData(**(await state.get_data()))
    async with context.session_maker.begin() as session:
        assert data.chat_id
        if tg := await get_destinations(data.chat_id, data.thread_id, session):
            if not callback_data.enabled:
                await add_forwarding(
                    callback_data.id,
                    tg.chat.original_id,
                    tg.get_thread_id(),
                    session,
                )
            else:
                await delete_forwarding(
                    callback_data.id,
                    tg.chat.original_id,
                    tg.get_thread_id(),
                    session,
                )
            keyboard = await build_channel_keyboard(
                tg.chat.original_id,
                tg.get_thread_original_id(),
                from_user.id in context.settings.bot.admin_ids,
                data.channels_menu_offset,
                MAX_YT_CHANNEL_COUNT,
                data.selected_categories,
                session,
            )
            await message.edit_reply_markup(reply_markup=keyboard)
    await state.set_data(data.model_dump())


@router.callback_query(TgData.filter(), F.message.as_("message"))
async def yt_channels_in_tg_pressed(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    callback_data: TgData,
    context: BotContext,
):
    data = schemas.StateData(**(await state.get_data()))
    data.chat_id = callback_data.chat_id
    data.thread_id = callback_data.thread_id

    async with context.session_maker.begin() as session:
        keyboard = await build_category_filter_keyboard(
            data.categories_menu_offset,
            MAX_CATEGORY_COUNT,
            data.selected_categories,
            session,
        )
        await message.edit_text("YouTube channels:", reply_markup=keyboard)

    await state.set_data(data.model_dump())


@router.callback_query(
    BackData.filter(),
    F.message.as_("message"),
    F.from_user.as_("from_user"),
)
async def handle_back(
    query: CallbackQuery,
    state: FSMContext,
    message: Message,
    from_user: User,
    bot: Bot,
    context: BotContext,
):
    data = schemas.StateData(**(await state.get_data()))
    _current_state = data.history.pop()
    prev_state = data.history.back()
    await state.set_data(data.model_dump())

    if not prev_state:
        logger.warning("Wrong history!")
        return

    match prev_state:
        case Menu.MAIN.state:
            is_owner = from_user.id in context.settings.bot.admin_ids
            await show_main_keyboard(message, is_owner, bot, state)
        case Menu.TELEGRAMS.state:
            await show_telegrams_menu(query, state, message, context)
        case Menu.CATEGORIES.state:
            await show_categories_menu(query, state, message, context)
        case Menu.ATTACH_CATEGORIES.state:
            await show_channels_menu(query, state, message, from_user, context)


@router.callback_query(CloseData.filter(), F.message.as_("message"))
async def handle_close(_query: CallbackQuery, message: Message):
    await message.delete()
