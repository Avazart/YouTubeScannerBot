import logging

import aiohttp
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from ..bot_types import BotContext, StorageKey, Data
from ..bot_types import StatusData, Keyboard, NavData
from ..keyboards import (
    AttachCategoryData,
    YTChannelCategoryData,
    build_telegram_tg_keyboard,
)
from ..keyboards import build_attach_categories_keyboard
from ...auxiliary_utils import split_string
from ...database.models import YouTubeChannel, Category
from ...database.utils import (
    delete_category_by_name,
    delete_channel_by_original_id,
    get_yt_channel_id,
)
from ...database.utils import (
    get_yt_channel_by_id,
    add_yt_channel_category,
    delete_yt_channel_category,
    set_telegram_chat_status,
)
from ...settings import MAX_CATEGORY_COUNT
from ...settings import MAX_TG_COUNT
from ...youtube_utils import get_channel_info

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(Command(commands="add_channel"))
async def add_channel_command(
    message: Message,
    command: CommandObject,
    context: BotContext,
):
    if args := command.args and split_string(command.args, " ", 1):
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


@router.message(Command(commands=["remove_channel"]))
async def remove_channel_command(
    message: Message,
    command: CommandObject,
    context: BotContext,
):
    # TODO: remove by channel_url, video_url, channel_id, channel_username
    try:
        if arg := command.args and command.args.strip():
            async with context.session_maker.begin() as session:
                if arg.startswith("https://"):
                    channel: YouTubeChannel = await get_channel_info(arg)
                    channel_id = channel.original_id
                else:
                    channel_id = arg
                await delete_channel_by_original_id(channel_id, session)
            await message.reply("Channel removed.")
        else:
            await message.reply("Channel url missing!")
    except Exception as e:
        await message.reply("I can't remove this channel!")
        raise e


@router.message(Command(commands=["add_category"]))
async def add_category(
    message: Message,
    command: CommandObject,
    context: BotContext,
):
    if command.args and (args := command.args.strip().split()):
        try:
            category_name, category_order = args[0], int(args[1])
            tag = Category(name=category_name, order=category_order)
            async with context.session_maker.begin() as session:
                await session.merge(tag)
            await message.reply("Successfully added.")
        except (ValueError, IndexError):
            await message.reply("Wrong args")
    else:
        await message.reply("Category name or/and order missing!")


@router.message(Command(commands=["remove_category"]))
async def remove_category(
    message: Message,
    command: CommandObject,
    context: BotContext,
):
    if category_name := command.args and command.args.strip():
        async with context.session_maker.begin() as session:
            await delete_category_by_name(category_name, session)
        await message.reply("Category removed.")
    else:
        await message.reply("Category name missing!")


@router.callback_query(AttachCategoryData.filter(), F.message.as_("message"))
async def attach_categories_callback(
    query: CallbackQuery,
    message: Message,
    callback_data: AttachCategoryData,
    context: BotContext,
):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavData(keyboard=Keyboard.YT_CHANNELS).pack()
        data.categories_offset = 0
        data.channel_id = callback_data.channel_id
        async with context.session_maker.begin() as session:
            if channel := await get_yt_channel_by_id(
                callback_data.channel_id,
                session,
            ):
                keyboard = await build_attach_categories_keyboard(
                    data.channel_id,
                    data.categories_offset,
                    MAX_CATEGORY_COUNT,
                    data.back_callback_data,
                    session,
                )
                await message.edit_text(
                    f'Select categories for "{channel.title}"',
                    reply_markup=keyboard,
                )
                await context.storage.set_data(key, data)


@router.callback_query(
    YTChannelCategoryData.filter(), F.message.as_("message")
)
async def yt_channel_category_button_pressed(
    query: CallbackQuery,
    message: Message,
    callback_data: YTChannelCategoryData,
    context: BotContext,
):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.session_maker.begin() as session:
            if callback_data.enabled:
                await delete_yt_channel_category(
                    callback_data.category_id,
                    callback_data.channel_id,
                    session,
                )
            else:
                await add_yt_channel_category(
                    callback_data.category_id,
                    callback_data.channel_id,
                    session,
                )
            keyboard = await build_attach_categories_keyboard(
                callback_data.channel_id,
                data.categories_offset,
                MAX_CATEGORY_COUNT,
                data.back_callback_data,
                session,
            )
            await message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(StatusData.filter(), F.message.as_("message"))
async def status_button_pressed(
    query: CallbackQuery,
    message: Message,
    callback_data: StatusData,
    context: BotContext,
):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.session_maker.begin() as session:
            await set_telegram_chat_status(
                callback_data.chat_id,
                callback_data.status,
                session,
            )
            keyboard = await build_telegram_tg_keyboard(
                data.tgs_offset,
                MAX_TG_COUNT,
                data.back_callback_data,
                session,
            )
            await message.edit_reply_markup(reply_markup=keyboard)
