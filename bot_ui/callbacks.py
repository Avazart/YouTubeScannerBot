from aiogram import Dispatcher, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from settings import MAX_TG_COUNT, MAX_TAG_COUNT, MAX_YT_CHANNEL_COUNT
from database.utils import (
    add_forwarding,
    delete_forwarding,
    get_yt_channel_by_id,
    add_yt_channel_tag,
    delete_yt_channel_tag,
    set_telegram_chat_status,
    get_destinations
)
from .bot_types import (
    BotContext,
    Data,
    StorageKey,
    TgData,
    StatusData,
    Keyboard,
    CloseData,
    NavigationData)
from .filers import ChatAdminFilter, BotAdminFilter
from .keyboards import (
    ChannelData,
    PageData,
    TagFilterData,
    AttachTagData,
    YtChannelTagData,
    build_main_keyboard,
    build_tag_filter_keyboard,
    build_telegram_tg_keyboard,
    build_channel_keyboard,
    build_attach_tags_keyboard
)


async def show_main_keyboard(key: StorageKey,
                             message: Message,
                             bot: Bot,
                             context: BotContext):
    is_owner = key.user_id == context.profile.owner_id
    keyboard = build_main_keyboard(is_owner)
    m = await message.answer("Main menu:", reply_markup=keyboard)
    if data := await context.storage.get_data(key):
        try:  # try remove keyboard
            if data.keyboard_id is not None:
                await bot.delete_message(message.chat.id, data.keyboard_id)
        except TelegramBadRequest:
            pass

    data = Data(m.message_id,
                original_chat_id=key.chat_id,
                original_thread_id=key.thread_id)
    await context.storage.set_data(key, data)


async def show_tag_filter_keyboard(query: CallbackQuery, context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavigationData(keyboard=Keyboard.MAIN).pack()
        data.tags_offset = 0
        async with context.SessionMaker.begin() as session:
            keyboard = await build_tag_filter_keyboard(data.tags_offset,
                                                       MAX_TAG_COUNT,
                                                       data.tags_ids,
                                                       data.back_callback_data,
                                                       session)
        await query.message.edit_text("Select tags for filter youtube channels:")
        await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


async def show_tg_keyboard(query: CallbackQuery, context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavigationData(keyboard=Keyboard.MAIN).pack()
        data.tgs_offset = 0
        async with context.SessionMaker.begin() as session:
            keyboard = await build_telegram_tg_keyboard(data.tgs_offset,
                                                        MAX_TG_COUNT,
                                                        data.back_callback_data,
                                                        session)
        await query.message.edit_text('Telegram chats and threads:')
        await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


async def show_channels_keyboard(query: CallbackQuery, context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavigationData(keyboard=Keyboard.TAG_FILTER).pack()
        data.yt_channels_offset = 0
        async with context.SessionMaker.begin() as session:
            keyboard = await build_channel_keyboard(data.original_chat_id,
                                                    data.original_thread_id,
                                                    key.user_id == context.profile.owner_id,
                                                    data.yt_channels_offset,
                                                    MAX_YT_CHANNEL_COUNT,
                                                    data.tags_ids,
                                                    data.back_callback_data,
                                                    session)
        await query.message.edit_text("YouTube channels:")
        await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


async def yt_channels_in_tg_pressed(query: CallbackQuery,
                                    callback_data: TgData,
                                    context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.original_chat_id = callback_data.chat_id
        data.original_thread_id = callback_data.thread_id
        data.back_callback_data = NavigationData(keyboard=Keyboard.TG_OBJECTS).pack()
        async with context.SessionMaker.begin() as session:
            keyboard = await build_tag_filter_keyboard(data.tags_offset,
                                                       MAX_TAG_COUNT,
                                                       data.tags_ids,
                                                       data.back_callback_data,
                                                       session)
            await query.message.edit_text("YouTube channels:")  # TODO: For telegram
            await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


async def channel_checked(query: CallbackQuery,
                          callback_data: ChannelData,
                          context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.SessionMaker.begin() as session:
            tg = await get_destinations(data.original_chat_id, data.original_thread_id, session)
            if not callback_data.enabled:
                await add_forwarding(callback_data.id,
                                     tg.chat.original_id,
                                     tg.get_thread_id(),
                                     session)
            else:
                await delete_forwarding(callback_data.id,
                                        tg.chat.original_id,
                                        tg.get_thread_id(),
                                        session)

        async with context.SessionMaker.begin() as session:
            keyboard = await build_channel_keyboard(tg.chat.original_id,
                                                    tg.get_thread_original_id(),
                                                    key.user_id == context.profile.owner_id,
                                                    data.yt_channels_offset,
                                                    MAX_YT_CHANNEL_COUNT,
                                                    data.tags_ids,
                                                    data.back_callback_data,
                                                    session)
            await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


async def tag_button_pressed(query: CallbackQuery,
                             callback_data: TagFilterData,
                             context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.SessionMaker.begin() as session:
            data.tags_ids ^= {callback_data.id, }
            keyboard = await build_tag_filter_keyboard(data.tags_offset,
                                                       MAX_TAG_COUNT,
                                                       data.tags_ids,
                                                       data.back_callback_data,
                                                       session)
            await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


async def close_keyboard(query: CallbackQuery):
    await query.message.delete()


async def back_to_main_keyboard(query: CallbackQuery, bot: Bot, context: BotContext):
    await show_main_keyboard(StorageKey.from_callback_query(query),
                             query.message,
                             bot,
                             context)


async def attach_tags_callback(query: CallbackQuery,
                               callback_data: AttachTagData,
                               context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        data.back_callback_data = NavigationData(keyboard=Keyboard.YT_CHANNELS).pack()
        data.tags_offset = 0
        data.original_channel_id = callback_data.channel_id
        async with context.SessionMaker.begin() as session:
            if channel := await get_yt_channel_by_id(callback_data.channel_id, session):
                keyboard = await build_attach_tags_keyboard(data.original_channel_id,
                                                            data.tags_offset,
                                                            MAX_TAG_COUNT,
                                                            data.back_callback_data,
                                                            session)
                await query.message.edit_text(f'Select tag for "{channel.title}"')
                await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


async def yt_channel_tag_button_pressed(query: CallbackQuery,
                                        callback_data: YtChannelTagData,
                                        context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.SessionMaker.begin() as session:
            if callback_data.enabled:
                await delete_yt_channel_tag(callback_data.tag_id, callback_data.channel_id, session)
            else:
                await add_yt_channel_tag(callback_data.tag_id, callback_data.channel_id, session)

            keyboard = await build_attach_tags_keyboard(callback_data.channel_id,
                                                        data.tags_offset,
                                                        MAX_TAG_COUNT,
                                                        data.back_callback_data,
                                                        session)
            await query.message.edit_reply_markup(reply_markup=keyboard)


async def status_button_pressed(query: CallbackQuery,
                                callback_data: StatusData,
                                context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.SessionMaker.begin() as session:
            await set_telegram_chat_status(callback_data.chat_id,
                                           callback_data.status,
                                           session)
            keyboard = await build_telegram_tg_keyboard(data.tgs_offset,
                                                        MAX_TG_COUNT,
                                                        data.back_callback_data,
                                                        session)
            await query.message.edit_reply_markup(reply_markup=keyboard)


async def nav_button_pressed(query: CallbackQuery,
                             callback_data: PageData,
                             context: BotContext):
    key = StorageKey.from_callback_query(query)
    if data := await context.storage.get_data(key):
        async with context.SessionMaker.begin() as session:
            match callback_data.keyboard:
                case Keyboard.TAG_FILTER:
                    data.tags_offset = callback_data.offset
                    keyboard = await build_tag_filter_keyboard(data.tags_offset,
                                                               MAX_TAG_COUNT,
                                                               data.tags_ids,
                                                               data.back_callback_data,
                                                               session)
                case Keyboard.TG_OBJECTS:
                    data.tgs_offset = callback_data.offset
                    keyboard = await build_telegram_tg_keyboard(data.tgs_offset,
                                                                MAX_TG_COUNT,
                                                                data.back_callback_data,
                                                                session)
                case Keyboard.YT_CHANNELS:
                    data.yt_channels_offset = callback_data.offset
                    keyboard = await build_channel_keyboard(data.original_chat_id,
                                                            data.original_thread_id,
                                                            key.user_id == context.profile.owner_id,
                                                            data.yt_channels_offset,
                                                            MAX_YT_CHANNEL_COUNT,
                                                            data.tags_ids,
                                                            data.back_callback_data,
                                                            session)
                case Keyboard.ATTACH_TAGS:
                    data.tags_offset = callback_data.offset
                    keyboard = await build_attach_tags_keyboard(data.original_channel_id,
                                                                data.tags_offset,
                                                                MAX_TAG_COUNT,
                                                                data.back_callback_data,
                                                                session)
            await query.message.edit_reply_markup(reply_markup=keyboard)
        await context.storage.set_data(key, data)


def register_callback_queries(dp: Dispatcher,
                              chat_admin_filter: ChatAdminFilter,
                              bot_admin_filter: BotAdminFilter):
    callback_queries = (
        (back_to_main_keyboard, chat_admin_filter, NavigationData.filter(F.keyboard == Keyboard.MAIN)),
        (show_tag_filter_keyboard, chat_admin_filter, NavigationData.filter(F.keyboard == Keyboard.TAG_FILTER)),
        (show_channels_keyboard, chat_admin_filter, NavigationData.filter(F.keyboard == Keyboard.YT_CHANNELS)),
        (show_tg_keyboard, chat_admin_filter, NavigationData.filter(F.keyboard == Keyboard.TG_OBJECTS)),
        (close_keyboard, chat_admin_filter, CloseData.filter()),

        (nav_button_pressed, chat_admin_filter, PageData.filter()),
        (tag_button_pressed, chat_admin_filter, TagFilterData.filter()),
        (channel_checked, chat_admin_filter, ChannelData.filter()),
        (yt_channels_in_tg_pressed, chat_admin_filter, TgData.filter()),

        # bot admin
        (attach_tags_callback, bot_admin_filter, AttachTagData.filter()),
        (yt_channel_tag_button_pressed, bot_admin_filter, YtChannelTagData.filter()),
        (status_button_pressed, bot_admin_filter, StatusData.filter()),
    )
    for callback_query in callback_queries:
        dp.callback_query.register(*callback_query)
