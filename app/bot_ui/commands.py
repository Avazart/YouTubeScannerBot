from logging import getLogger
from typing import no_type_check

import aiohttp
from aiogram import Dispatcher
from aiogram.client.bot import Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from .bot_types import BotContext, StorageKey, Status, Data
from .callbacks import show_main_keyboard
from .filers import ChatAdminFilter, BotAdminFilter
from .keyboards import build_attach_categories_keyboard
from ..settings import MIN_MEMBER_COUNT, MAX_CATEGORY_COUNT
from ..youtube_utils import get_channel_info
from ..auxiliary_utils import get_thread_id, split_string
from ..database.models import YouTubeChannel, Category, TelegramChat, TelegramThread
from ..database.utils import (
    get_destinations,
    get_yt_channel_id,
    delete_category_by_name,
    delete_channel_by_original_id
)

logger = getLogger(__name__)


async def start_command(message: Message):
    await message.answer(
        "I periodically scan YouTube channels "
        "for new videos and send you links to them in Telegram\n\n"
        "You can control me by sending these commands:\n\n"
        "/menu - open the menu\n\n"
        "/add_channel <url> - add youtube channel")


async def menu_command(message: Message, bot: Bot, context: BotContext):
    async with context.session_maker.begin() as session:
        thread_original_id = get_thread_id(message)
        if tg := await get_destinations(message.chat.id,
                                        thread_original_id,
                                        session):
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
                original_chat_id=message.chat.id
            )
            await session.merge(thread)
    await show_main_keyboard(
        StorageKey.from_message(message),
        message,
        bot,
        context
    )


async def add_channel_command(message: Message,
                              command: CommandObject,
                              bot: Bot,
                              context: BotContext):
    """
        This command works only for chat admins and admins of the bot.
        In group chats, this command only works if
        the group has more than 10 members.
        In private chats, this command is only available to admins of the bot.
    """

    if not message.from_user:
        return

    #  TODO: Move this checking to Filter
    if message.chat.type.lower() == 'private':
        if message.from_user.id not in context.settings.bot_admin_ids:
            return
    elif await bot.get_chat_member_count(message.chat.id) < MIN_MEMBER_COUNT:
        return

    if args := command.args and split_string(command.args,
                                             sep=' ',
                                             max_split=1):
        try:
            channel: YouTubeChannel = await get_channel_info(args[0])
        except aiohttp.ClientError as e:
            logger.error(f"{type(e)} {e}")
            await message.reply("I can't add this channel!")
            return

        async with context.session_maker() as session:
            channel.id = await get_yt_channel_id(channel.original_id,
                                                 session)
            already_exists = channel.id is not None
            if already_exists:
                await session.merge(channel)
            else:
                session.add(channel)
            await session.commit()

            result = 'already exists!' \
                if already_exists \
                else 'successfully added.'
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
                session
            )
            text = f'Select categories for "{channel.title}"'
            await message.answer(text, reply_markup=keyboard)
            await context.storage.set_data(key, data)


async def remove_channel_command(message: Message,
                                 command: CommandObject,
                                 context: BotContext):
    # TODO: remove by channel_url, video_url, channel_id, channel_username
    try:
        if arg := command.args and command.args.strip():
            async with context.session_maker.begin() as session:
                if arg.startswith('https://'):
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


async def add_category(message: Message,
                       command: CommandObject,
                       context: BotContext):
    if args := command.args.strip().split():
        try:
            category_name, category_order = args[0], int(args[1])
            tag = Category(name=category_name, order=category_order)
            async with context.session_maker.begin() as session:
                await session.merge(tag)
            await message.reply("Successfully added.")
        except ValueError:
            await message.reply("Wrong args")
    else:
        await message.reply("Category name or/and order missing!")


async def remove_category(message: Message,
                          command: CommandObject,
                          context: BotContext):
    if category_name := command.args and command.args.strip():
        async with context.session_maker.begin() as session:
            await delete_category_by_name(category_name, session)
        await message.reply("Category removed.")
    else:
        await message.reply("Category name missing!")


@no_type_check
def register_commands(dp: Dispatcher,
                      chat_admin_filter: ChatAdminFilter,
                      bot_admin_filter: BotAdminFilter):
    commands = (
        (
            start_command,
            chat_admin_filter,
            Command(commands=['start', 'help'])
        ),
        (
            menu_command,
            chat_admin_filter,
            Command(commands=['menu', ])
        ),
        (
            add_channel_command,
            chat_admin_filter,
            Command(commands=['add_channel', ])
        ),

        (
            add_category,
            bot_admin_filter,
            Command(commands=['add_category', ])
        ),
        (
            remove_category,
            bot_admin_filter,
            Command(commands=['remove_category', ])
        ),
        (
            remove_channel_command,
            bot_admin_filter,
            Command(commands=['remove_channel', ])
        )
    )
    for command in commands:
        dp.message.register(*command)
