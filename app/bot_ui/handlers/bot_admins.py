import logging

import aiohttp
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ...auxiliary_utils import split_string
from ...constants import MAX_CATEGORY_COUNT, MAX_TG_COUNT
from ...database.models import Category, YouTubeChannel
from ...database.utils import (
    add_yt_channel_category,
    delete_category_by_name,
    delete_channel_by_original_id,
    delete_yt_channel_category,
    get_yt_channel_by_id,
    get_yt_channel_id,
    set_telegram_chat_status,
)
from ...youtube_utils import get_channel_info
from .. import schemas
from ..bot_types import BotContext, Menu, StatusData
from ..keyboards import (
    AttachCategoryData,
    YTChannelCategoryData,
    build_attach_categories_keyboard,
    build_telegram_tg_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(Command(commands="add_channel"))
async def add_channel_command(
    message: Message,
    command: CommandObject,
    context: BotContext,
    state: FSMContext,
):
    if args := command.args and split_string(command.args, " ", 1):
        try:
            channel: YouTubeChannel = await get_channel_info(args[0])
        except aiohttp.ClientError as e:
            logger.error("%s %s", type(e), e)
            await message.reply("I can't add this channel!")
            return

        async with context.session_maker() as session:
            channel_id = await get_yt_channel_id(channel.original_id, session)
            assert channel_id is not None
            channel.id = channel_id
            already_exists = channel.id is not None
            if already_exists:
                await session.merge(channel)
            else:
                session.add(channel)
            await session.commit()

            if already_exists:
                result = "already exists!"
            else:
                result = "successfully added."
            text = f'ChannelMenuData "{channel.title}" {result}'
            await message.reply(text)

            # ATTACH CATEGORY
            keyboard = await build_attach_categories_keyboard(
                yt_channel_id=channel.id,
                offset=0,
                count=MAX_CATEGORY_COUNT,
                session=session,
            )
            text = f'Select categories for "{channel.title}"'
            await message.answer(text, reply_markup=keyboard)
            await state.set_state(Menu.CATEGORIES)

            data = schemas.StateData(
                channel_id=channel.id,
                categories_menu_offset=0,
            )
            await state.set_data(data.model_dump())


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
            await message.reply("ChannelMenuData removed.")
        else:
            await message.reply("ChannelMenuData url missing!")
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
            category = Category(name=category_name, order=category_order)
            async with context.session_maker.begin() as session:
                await session.merge(category)
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
    _query: CallbackQuery,
    message: Message,
    callback_data: AttachCategoryData,
    context: BotContext,
    state: FSMContext,
):
    logger.debug("attach_categories_callback")

    data = schemas.StateData(**(await state.get_data()))
    async with context.session_maker.begin() as session:
        data.channel_id = callback_data.channel_id
        if channel := await get_yt_channel_by_id(data.channel_id, session):
            logger.debug("channel: %s", channel.title)
            keyboard = await build_attach_categories_keyboard(
                data.channel_id,
                data.categories_menu_offset,
                MAX_CATEGORY_COUNT,
                session,
            )
            await state.set_data(data.model_dump())
            text = f'Select categories for "{channel.title}"'
            await message.edit_text(text, reply_markup=keyboard)


@router.callback_query(
    YTChannelCategoryData.filter(), F.message.as_("message")
)
async def yt_channel_category_button_pressed(
    _query: CallbackQuery,
    message: Message,
    callback_data: YTChannelCategoryData,
    context: BotContext,
    state: FSMContext,
):
    # data = schemas.StateData(**(await state.get_data()))
    # assert data.category_id is not None

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
            callback_data.category_id,
            MAX_CATEGORY_COUNT,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(StatusData.filter(), F.message.as_("message"))
async def status_button_pressed(
    _query: CallbackQuery,
    message: Message,
    callback_data: StatusData,
    context: BotContext,
    state: FSMContext,
):
    data = schemas.StateData(**(await state.get_data()))
    assert data.telegrams_menu_offset is not None

    async with context.session_maker.begin() as session:
        await set_telegram_chat_status(
            callback_data.chat_id,
            callback_data.status,
            session,
        )
        keyboard = await build_telegram_tg_keyboard(
            data.telegrams_menu_offset,
            MAX_TG_COUNT,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)
