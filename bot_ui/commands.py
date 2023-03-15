from aiogram import Dispatcher
from aiogram.client.bot import Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from auxiliary_utils import get_thread_id, split_string
from bot_ui.bot_types import BotContext, StorageKey, Status
from database.models import YouTubeChannel, Tag, TelegramChat, TelegramThread, YouTubeChannelTag
from database.utils import (
    get_destinations,
    get_tag_id_by_name,
    get_yt_channel_id_by_original_id,
    delete_tag_by_name,
    delete_channel_by_original_id
)
from settings import MIN_MEMBER_COUNT
from youtube_utils import get_channel_info

from .callbacks import show_main_keyboard
from .filers import ChatAdminFilter, BotAdminFilter


async def start_command(message: Message):
    await message.answer(
        "I periodically scan YouTube channels "
        "for new videos and send you links to them in Telegram\n\n"
        "You can control me by sending these commands:\n\n"
        "/menu - open the menu\n\n"
        "/add_channel <url> - add youtube channel")


async def menu_command(message: Message, bot: Bot, context: BotContext):
    async with context.SessionMaker.begin() as session:
        thread_original_id = get_thread_id(message)
        if tg := await get_destinations(message.chat.id, thread_original_id, session):
            chat = tg.chat
            if chat.status == Status.BAN:
                return
            chat.status = Status.ON
        else:
            chat = TelegramChat.from_aiogram_chat(message.chat)
        await session.merge(chat)

        if thread_original_id is not None:
            thread = TelegramThread(id=tg.thread.id if tg else None,
                                    original_id=thread_original_id,
                                    original_chat_id=message.chat.id)
            await session.merge(thread)
    await show_main_keyboard(StorageKey.from_message(message), message, bot, context)


async def is_allowed_for_add_channel(bot: Bot, message: Message, bot_admin_ids) -> bool:
    if message.chat.type.lower() == 'private':
        return (message.from_user.id in bot_admin_ids) or \
               (await bot.get_chat_members_count(message.chat.id) >= MIN_MEMBER_COUNT)
    return True


async def add_channel_command(message: Message,
                              command: CommandObject,
                              bot: Bot,
                              context: BotContext):
    if await is_allowed_for_add_channel(bot, message, context.settings.bot_admin_ids):
        try:
            if args := command.args and split_string(command.args, sep=' ', max_split=1):
                channel: YouTubeChannel = await get_channel_info(args[0])
                tag_names = split_string(args[1], ',') if len(args) == 2 else []

                async with context.SessionMaker.begin() as session:
                    channel.id = await get_yt_channel_id_by_original_id(channel.original_id, session)
                    await session.merge(channel)

                async with context.SessionMaker.begin() as session:
                    for tag_name in tag_names:
                        tag_id = await get_tag_id_by_name(tag_name, session)
                        if tag_id is None:
                            await message.reply(f'Tag with name "{tag_name}" not found!')
                            return
                        yt_tag = YouTubeChannelTag(tag_id=tag_id, channel_id=channel.id)
                        await session.merge(yt_tag)
                    await message.reply("Successfully added.")
            else:
                await message.reply("Url missing!")
                return
        except Exception as e:
            await message.reply("I can't add this channel!")
            raise e
    else:
        await message.reply("This operation is not allowed for this chat!")


async def remove_channel(message: Message, command: CommandObject, context: BotContext):
    try:
        if url := command.args and command.args.strip():
            async with context.SessionMaker.begin() as session:
                channel: YouTubeChannel = await get_channel_info(url)
                await delete_channel_by_original_id(channel.original_id, session)
            await message.reply("Channel removed.")
        else:
            await message.reply("Channel url missing!")
    except Exception as e:
        await message.reply("I can't remove this channel!")
        raise e


async def add_tag(message: Message, command: CommandObject, context: BotContext):
    if tag_name := command.args and command.args.strip():
        tag = Tag(name=tag_name)
        async with context.SessionMaker.begin() as session:
            await session.merge(tag)
        await message.reply("Successfully added.")
    else:
        await message.reply("Tag name missing!")


async def remove_tag(message: Message, command: CommandObject, context: BotContext):
    if tag_name := command.args and command.args.strip():
        async with context.SessionMaker.begin() as session:
            await delete_tag_by_name(tag_name, session)
        await message.reply("Tag removed.")
    else:
        await message.reply("Tag name missing!")


def register_commands(dp: Dispatcher,
                      chat_admin_filter: ChatAdminFilter,
                      bot_admin_filter: BotAdminFilter):
    commands = (
        (start_command, chat_admin_filter, Command(commands=['start', 'help'])),
        (menu_command, chat_admin_filter, Command(commands=['menu', ])),
        (add_channel_command, chat_admin_filter, Command(commands=['add_channel', ])),

        (add_tag, bot_admin_filter, Command(commands=['add_tag', ])),
        (remove_tag, bot_admin_filter, Command(commands=['remove_tag', ])),
        (remove_channel, bot_admin_filter, Command(commands=['remove_channel', ]))
    )
    for command in commands:
        dp.message.register(*command)
