import logging

import aiohttp
from aiogram import F, Router
from aiogram.client.bot import Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from ..bot_types import BotContext, StorageKey, Status, Data
from ..bot_types import TgData, Keyboard, CloseData, NavData
from ..keyboards import (
    ChannelData,
    PageData,
    CategoryFilterData,
    build_category_filter_keyboard,
    build_telegram_tg_keyboard,
    build_channel_keyboard,
    build_main_keyboard,
)
from ..keyboards import build_attach_categories_keyboard
from ...auxiliary_utils import get_thread_id, split_string
from ...database.models import YouTubeChannel, TelegramChat, TelegramThread
from ...database.utils import add_forwarding, delete_forwarding
from ...database.utils import get_destinations, get_yt_channel_id
from ...settings import MAX_TG_COUNT, MAX_CATEGORY_COUNT, MAX_YT_CHANNEL_COUNT
from ...settings import MIN_MEMBER_COUNT
from ...youtube_utils import get_channel_info

logger = logging.getLogger(__name__)
router = Router(name=__name__)


async def show_main_keyboard(
    key: StorageKey,
    message: Message,
    bot: Bot,
    context: BotContext,
):
    is_owner = key.user_id in context.settings.bot_admin_ids
    keyboard = build_main_keyboard(is_owner)
    m = await message.answer("Main menu:", reply_markup=keyboard)
    if data := await context.storage.get_data(key):
        try:  # try remove keyboard
            if data.keyboard_id is not None:
                await bot.delete_message(message.chat.id, data.keyboard_id)
        except TelegramBadRequest:
            pass

    data = Data(
        m.message_id,
        original_chat_id=key.chat_id,
        original_thread_id=key.thread_id,
    )
    await context.storage.set_data(key, data)


@router.message(Command(commands=["start", "help"]))
async def start_command(message: Message):
    logger.debug(f"{message.chat.type=}")
    await message.answer(
        "I periodically scan YouTube channels "
        "for new videos and send you links to them in Telegram\n\n"
        "You can control me by sending these commands:\n\n"
        "/menu - open the menu\n\n"
        "/add_channel <url> - add youtube channel"
    )


@router.message(Command(commands=["menu"]))
async def menu_command(message: Message, bot: Bot, context: BotContext):
    async with context.session_maker.begin() as session:
        thread_original_id = get_thread_id(message)
        if tg := await get_destinations(
            message.chat.id, thread_original_id, session
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
    await show_main_keyboard(
        StorageKey.from_message(message),
        message,
        bot,
        context,
    )


@router.message(Command(commands=["add_channel"]))
async def add_channel_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    context: BotContext,
):
    """
    This command works only for chat admins and admins of the bot.
    In group chats, this command only works if
    the group has more than 10 members.
    In private chats, this command is only available to admins of the bot.
    """

    if not message.from_user:
        return

    #  TODO: Move this checking to Filter ?
    if message.chat.type.lower() == "private":
        if message.from_user.id not in context.settings.bot_admin_ids:
            return
    elif await bot.get_chat_member_count(message.chat.id) < MIN_MEMBER_COUNT:
        return

    if args := command.args and split_string(
        command.args, sep=" ", max_split=1
    ):
        try:
            channel: YouTubeChannel = await get_channel_info(args[0])
        except aiohttp.ClientError as e:
            logger.error(f"{type(e)} {e}")
            await message.reply("I can't add this channel!")
            return

        async with context.session_maker() as session:
            channel.id = await get_yt_channel_id(channel.original_id, session)
            already_exists = channel.id is not None
            if already_exists:
                await session.merge(channel)
            else:
                session.add(channel)
            await session.commit()

            result = (
                "already exists!" if already_exists else "successfully added."
            )
            text = f'Channel "{channel.title}" {result}'
            await message.reply(text)

            key = StorageKey.from_message(message)
            data = Data(channel_id=channel.id)
            assert data.channel_id is not None
            keyboard = await build_attach_categories_keyboard(
                data.channel_id,
                data.categories_offset,
                MAX_CATEGORY_COUNT,
                data.back_callback_data,
                session,
            )
            text = f'Select categories for "{channel.title}"'
            await message.answer(text, reply_markup=keyboard)
            await context.storage.set_data(key, data)


@router.callback_query(NavData.filter(F.keyboard == Keyboard.CATEGORY_FILTER))
async def show_category_filter_keyboard(
    query: CallbackQuery,
    context: BotContext,
):
    if query.message is None:
        return

    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavData(keyboard=Keyboard.MAIN).pack()
        data.categories_offset = 0
        async with context.session_maker.begin() as session:
            keyboard = await build_category_filter_keyboard(
                data.categories_offset,
                MAX_CATEGORY_COUNT,
                data.categories_ids,
                data.back_callback_data,
                session,
            )
            await query.message.edit_text(
                "Select categories for filter youtube channels:",
                reply_markup=keyboard,
            )
            await context.storage.set_data(key, data)


@router.callback_query(NavData.filter(F.keyboard == Keyboard.YT_CHANNELS))
async def show_channels_keyboard(query: CallbackQuery, context: BotContext):
    if query.message is None:
        return

    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavData(
            keyboard=Keyboard.CATEGORY_FILTER
        ).pack()
        data.yt_channels_offset = 0
        async with context.session_maker.begin() as session:
            assert data.original_chat_id  # FIXME
            keyboard = await build_channel_keyboard(
                data.original_chat_id,
                data.original_thread_id,
                key.user_id in context.settings.bot_admin_ids,
                data.yt_channels_offset,
                MAX_YT_CHANNEL_COUNT,
                data.categories_ids,
                data.back_callback_data,
                session,
            )
            await query.message.edit_text(
                "YouTube channels:", reply_markup=keyboard
            )
            await context.storage.set_data(key, data)


@router.callback_query(CloseData.filter())
async def close_keyboard(query: CallbackQuery):
    if query.message:
        await query.message.delete()


@router.callback_query(NavData.filter(F.keyboard == Keyboard.MAIN))
async def back_to_main_keyboard(
    query: CallbackQuery,
    bot: Bot,
    context: BotContext,
):
    if query.message:
        key = StorageKey.from_callback_query(query)
        await show_main_keyboard(key, query.message, bot, context)


@router.callback_query(NavData.filter(F.keyboard == Keyboard.TG_OBJECTS))
async def show_tg_keyboard(query: CallbackQuery, context: BotContext):
    logger.debug("Telegram chats and threads")

    if query.message is None:
        return

    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavData(keyboard=Keyboard.MAIN).pack()
        data.tgs_offset = 0
        async with context.session_maker.begin() as session:
            keyboard = await build_telegram_tg_keyboard(
                data.tgs_offset, MAX_TG_COUNT, data.back_callback_data, session
            )
            await query.message.edit_text(
                "Telegram chats and threads:", reply_markup=keyboard
            )
            await context.storage.set_data(key, data)


@router.callback_query(PageData.filter())
async def nav_button_pressed(
    query: CallbackQuery,
    callback_data: PageData,
    context: BotContext,
):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.session_maker.begin() as session:
            match callback_data.keyboard:
                case Keyboard.CATEGORY_FILTER:
                    data.categories_offset = callback_data.offset
                    keyboard = await build_category_filter_keyboard(
                        data.categories_offset,
                        MAX_CATEGORY_COUNT,
                        data.categories_ids,
                        data.back_callback_data,
                        session,
                    )
                case Keyboard.TG_OBJECTS:
                    data.tgs_offset = callback_data.offset
                    keyboard = await build_telegram_tg_keyboard(
                        data.tgs_offset,
                        MAX_TG_COUNT,
                        data.back_callback_data,
                        session,
                    )
                case Keyboard.YT_CHANNELS:
                    data.yt_channels_offset = callback_data.offset
                    assert data.original_chat_id is not None  # FIXME
                    keyboard = await build_channel_keyboard(
                        data.original_chat_id,
                        data.original_thread_id,
                        key.user_id in context.settings.bot_admin_ids,
                        data.yt_channels_offset,
                        MAX_YT_CHANNEL_COUNT,
                        data.categories_ids,
                        data.back_callback_data,
                        session,
                    )
                case Keyboard.ATTACH_CATEGORIES:
                    data.categories_offset = callback_data.offset
                    assert data.channel_id is not None
                    keyboard = await build_attach_categories_keyboard(
                        data.channel_id,
                        data.categories_offset,
                        MAX_CATEGORY_COUNT,
                        data.back_callback_data,
                        session,
                    )
            assert query.message
            await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


@router.callback_query(CategoryFilterData.filter())
async def category_button_pressed(
    query: CallbackQuery,
    callback_data: CategoryFilterData,
    context: BotContext,
):
    if query.message is None:
        return
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.session_maker.begin() as session:
            data.categories_ids ^= {
                callback_data.id,
            }
            keyboard = await build_category_filter_keyboard(
                data.categories_offset,
                MAX_CATEGORY_COUNT,
                data.categories_ids,
                data.back_callback_data,
                session,
            )
            await query.message.edit_reply_markup(reply_markup=keyboard)
            await context.storage.set_data(key, data)


@router.callback_query(ChannelData.filter())
async def channel_checked(
    query: CallbackQuery,
    callback_data: ChannelData,
    context: BotContext,
):
    if query.message is None:
        return

    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.session_maker.begin() as session:
            assert data.original_chat_id  # FIXME
            if tg := await get_destinations(
                data.original_chat_id,
                data.original_thread_id,
                session,
            ):
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
                    key.user_id in context.settings.bot_admin_ids,
                    data.yt_channels_offset,
                    MAX_YT_CHANNEL_COUNT,
                    data.categories_ids,
                    data.back_callback_data,
                    session,
                )
                assert query.message
                await query.message.edit_reply_markup(reply_markup=keyboard)
            await context.storage.set_data(key, data)


@router.callback_query(TgData.filter())
async def yt_channels_in_tg_pressed(
    query: CallbackQuery,
    callback_data: TgData,
    context: BotContext,
):
    if query.message is None:
        return

    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.original_chat_id = callback_data.chat_id
        data.original_thread_id = callback_data.thread_id
        data.back_callback_data = NavData(keyboard=Keyboard.TG_OBJECTS).pack()
        async with context.session_maker.begin() as session:
            keyboard = await build_category_filter_keyboard(
                data.categories_offset,
                MAX_CATEGORY_COUNT,
                data.categories_ids,
                data.back_callback_data,
                session,
            )
            assert query.message
            await query.message.edit_text(
                "YouTube channels:",
                reply_markup=keyboard,
            )
            # TODO: For telegram
        await context.storage.set_data(key, data)
