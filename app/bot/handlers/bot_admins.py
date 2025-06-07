import logging

import aiohttp
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ...constants import MAX_CATEGORY_COUNT, MAX_TG_COUNT
from ...database.models import YouTubeChannel
from ...database.services import (
    CategoryService,
    TelegramService,
    YTChannelCategoryService,
    YTChannelService,
)
from ...jobs import notify, scan
from ...youtube_utils import get_channel_info
from ..bot_types import BotContext, Menu, StatusData
from ..keyboards import (
    AttachCategoryData,
    YTChannelCategoryData,
    build_attach_categories_keyboard,
    build_telegram_tg_keyboard,
)
from ..state_history import StateHistory

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(Command(commands="add_channel"))
async def add_channel_command(
    message: Message,
    command: CommandObject,
    context: BotContext,
    state: FSMContext,
):
    if command.args and (channel_url := command.args.strip()):
        try:
            site_channel: YouTubeChannel = await get_channel_info(channel_url)
        except aiohttp.ClientError as e:
            logger.error("%s %s", type(e), e)
            await message.reply("I can't add this channel!")
            return

        async with context.session_maker() as session:
            service = YTChannelService(session)
            if db_channel := await service.get_by_original_id(
                site_channel.original_id
            ):
                site_channel.id = db_channel.id
                await session.merge(site_channel)
                result = "already exists!"
            else:
                session.add(site_channel)
                result = "successfully added."

            text = f'ChannelMenuData "{site_channel.title}" {result}'
            await message.reply(text)
            await session.commit()

            category_offset = 0
            #  TODO:
            #  Don`t show BACK button
            keyboard = await build_attach_categories_keyboard(
                channel_id=site_channel.id,
                offset=category_offset,
                count=MAX_CATEGORY_COUNT,
                session=session,
            )
            text = f'Select categories for "{site_channel.title}"'
            await message.answer(text, reply_markup=keyboard)
            await state.update_data(
                {
                    "channel_id": site_channel.id,
                    "category_offset": category_offset,
                }
            )
            await state.set_state(Menu.CATEGORIES)


@router.message(Command(commands=["remove_channel"]))
async def remove_channel_command(
    message: Message,
    command: CommandObject,
    context: BotContext,
):
    # TODO: remove by channel_url, video_url, channel_id, channel_username
    try:
        if command.args and (channel_url_or_id := command.args.strip()):
            async with context.session_maker.begin() as session:
                if channel_url_or_id.startswith("https://"):
                    channel = await get_channel_info(channel_url_or_id)
                    channel_id = channel.original_id
                else:
                    channel_id = channel_url_or_id
                service = YTChannelService(session)
                await service.remove_by_original_id(channel_id)
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
    if command.args and (args := command.args.split(" ", maxsplit=1)):
        try:
            category_name, category_order = args[0], int(args[1])
            async with context.session_maker.begin() as session:
                category_service = CategoryService(session)
                await category_service.add(category_name, category_order)
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
    if command.args and (category_name := command.args.strip()):
        async with context.session_maker.begin() as session:
            category_service = CategoryService(session)
            await category_service.remove_by_name(category_name)
        await message.reply("Category removed.")
    else:
        await message.reply("Category name missing!")


@router.callback_query(AttachCategoryData.filter(), F.message.as_("message"))
async def show_attach_categories(
    _query: CallbackQuery,
    message: Message,
    callback_data: AttachCategoryData,
    context: BotContext,
    state: FSMContext,
):
    data = await state.get_data()
    history = StateHistory.from_list(data.get("history", []))
    attach_category_offset = data.get("attach_category_offset", 0)
    channel_id = callback_data.channel_id

    async with context.session_maker.begin() as session:
        channel_service = YTChannelService(session)
        if channel := await channel_service.get(channel_id):
            logger.debug("channel: %s", channel.title)
            keyboard = await build_attach_categories_keyboard(
                channel_id,
                attach_category_offset,
                MAX_CATEGORY_COUNT,
                session,
            )
            history.append(Menu.ATTACH_CATEGORIES)
            await state.update_data(
                {
                    "history": history.as_list(),
                    "channel_id": channel_id,
                    "attach_category_offset": attach_category_offset,
                }
            )
            await state.set_state(Menu.ATTACH_CATEGORIES)
            text = f'Select categories for "{channel.title}"'
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply("Channel not found")


@router.callback_query(
    YTChannelCategoryData.filter(), F.message.as_("message")
)
async def channel_category_checked(
    _query: CallbackQuery,
    message: Message,
    callback_data: YTChannelCategoryData,
    state: FSMContext,
    context: BotContext,
):
    data = await state.get_data()
    attach_category_offset = data.get("attach_category_offset", 0)

    async with context.session_maker.begin() as session:
        service = YTChannelCategoryService(session)
        if callback_data.enabled:
            await service.remove(
                callback_data.channel_id, callback_data.category_id
            )
        else:
            await service.add(
                callback_data.channel_id, callback_data.category_id
            )
        keyboard = await build_attach_categories_keyboard(
            callback_data.channel_id,
            attach_category_offset,
            MAX_CATEGORY_COUNT,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(
    Menu.TELEGRAMS, StatusData.filter(), F.message.as_("message")
)
async def status_button_pressed(
    _query: CallbackQuery,
    message: Message,
    callback_data: StatusData,
    context: BotContext,
    state: FSMContext,
):
    data = await state.get_data()
    telegram_offset = data.get("telegram_offset", 0)

    async with context.session_maker.begin() as session:
        service = TelegramService(session)
        await service.set_status(callback_data.chat_id, callback_data.status)
        keyboard = await build_telegram_tg_keyboard(
            telegram_offset,
            MAX_TG_COUNT,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)


@router.message(Command(commands=["scan"]))
async def scan_command(_message: Message, context: BotContext):
    await scan(context.session_maker, context.settings)


@router.message(Command(commands=["notify"]))
async def notify_command(_message: Message, bot: Bot, context: BotContext):
    await notify(context.session_maker, context.settings, bot)
