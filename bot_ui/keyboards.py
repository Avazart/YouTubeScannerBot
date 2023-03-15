from typing import Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from auxiliary_utils import evenly_batched
from bot_ui.bot_types import (
    PageData,
    ChannelData,
    AttachTagData,
    TagFilterData,
    YtChannelTagData,
    TgData,
    StatusData,
    Keyboard,
    NavigationData,
    CloseData
)
from database.models import YouTubeChannel, Tag, Status
from database.utils import Destination, get_yt_channels, get_tags, get_tgs, get_yt_channel_tags
from settings import KEYBOARD_COLUMN_COUNT


def _nav_buttons(prev_offset: Optional[int],
                 next_offset: Optional[int],
                 keyboard: Keyboard) -> list[InlineKeyboardButton]:
    nav_buttons = []
    if prev_offset is not None:
        prev_data = PageData(keyboard=keyboard, offset=prev_offset)
        prev_button = InlineKeyboardButton(text='⬅  Prev', callback_data=prev_data.pack())
        nav_buttons.append(prev_button)
    if next_offset is not None:
        next_data = PageData(keyboard=keyboard, offset=next_offset)
        next_button = InlineKeyboardButton(text='Next  ➡', callback_data=next_data.pack())
        nav_buttons.append(next_button)
    return nav_buttons


# MAIN

def build_main_keyboard(is_owner: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text='YouTube channels',
                              callback_data=NavigationData(keyboard=Keyboard.TAG_FILTER).pack())
         ]]
    if is_owner:
        button = \
            InlineKeyboardButton(text='Telegram chats and threads',
                                 callback_data=NavigationData(keyboard=Keyboard.TG_OBJECTS).pack()
                                 )
        buttons.append([button, ])

    buttons.append([InlineKeyboardButton(text='Close',
                                         callback_data=CloseData().pack()), ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# CHANNEL

def _channel_buttons(rows: list[YouTubeChannel],
                     back_callback_data: str,
                     is_owner: bool) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for channel, enabled in rows:
        text = f'{"✅" if enabled else " "} {channel.title}'
        data = ChannelData(id=channel.id, enabled=enabled, back_location=back_callback_data)
        check_button = InlineKeyboardButton(text=text, callback_data=data.pack())
        link_button = InlineKeyboardButton(text='Open in browser', url=channel.canonical_url)
        buttons.append([check_button, link_button])
        if is_owner:
            data = AttachTagData(channel_id=channel.id)
            tags_button = InlineKeyboardButton(text='Tags', callback_data=data.pack())
            buttons[-1].append(tags_button)
    return buttons


def _channel_keyboard(rows: list[YouTubeChannel],
                      is_owner: bool,
                      prev_offset: Optional[int],
                      next_offset: Optional[int],
                      back_callback_data: str) -> InlineKeyboardMarkup:
    buttons = _channel_buttons(rows, back_callback_data, is_owner)
    if nav_buttons := _nav_buttons(prev_offset, next_offset, Keyboard.YT_CHANNELS):
        buttons.append(nav_buttons)
    back_button = InlineKeyboardButton(text='Back', callback_data=back_callback_data)
    close_button = InlineKeyboardButton(text='Close', callback_data=CloseData().pack())
    buttons.append([back_button, close_button])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# TAG

def _tag_buttons(tags: list[Tag],
                 checked_tag_ids: set[int]) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for row in evenly_batched(tags, KEYBOARD_COLUMN_COUNT):
        row_buttons = []
        for tag in row:
            text = f'{"✅" if tag.id in checked_tag_ids else "🟩"} {tag.name}'
            data = TagFilterData(id=tag.id)
            tag_button = InlineKeyboardButton(text=text, callback_data=data.pack())
            row_buttons.append(tag_button)
        buttons.append(row_buttons)
    return buttons


def _tags_keyboard(tags: list[Tag],
                   checked_tag_ids: set[int],
                   prev_offset: Optional[int],
                   next_offset: Optional[int],
                   back_callback_data: str) -> InlineKeyboardMarkup:
    buttons = _tag_buttons(tags, checked_tag_ids)
    if nav_buttons := _nav_buttons(prev_offset, next_offset, Keyboard.TAG_FILTER):
        buttons.append(nav_buttons)
    back_button = InlineKeyboardButton(text='Back', callback_data=back_callback_data)
    close_button = InlineKeyboardButton(text='Close', callback_data=CloseData().pack())
    apply_button = \
        InlineKeyboardButton(text='Apply',
                             callback_data=NavigationData(keyboard=Keyboard.YT_CHANNELS).pack())
    buttons.append([back_button, close_button, apply_button])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ATTACH TAGS

def _attach_tags_buttons(tag_records: list[(Tag, bool)],
                         yt_channel_id: str) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for row in evenly_batched(tag_records, KEYBOARD_COLUMN_COUNT):
        row_buttons = []
        for tag, enable in row:
            text = f'{"✅" if enable else " "} {tag.name}'
            data = YtChannelTagData(tag_id=tag.id, channel_id=yt_channel_id, enabled=enable)
            tag_button = InlineKeyboardButton(text=text, callback_data=data.pack())
            row_buttons.append(tag_button)
        buttons.append(row_buttons)
    return buttons


def _attach_tags_keyboard(tag_records: list[(Tag, bool)],
                          yt_channel_id: str,
                          prev_offset: Optional[int],
                          next_offset: Optional[int],
                          back_callback_data: str) -> InlineKeyboardMarkup:
    buttons = _attach_tags_buttons(tag_records, yt_channel_id)
    if nav_buttons := _nav_buttons(prev_offset, next_offset, Keyboard.ATTACH_TAGS):
        buttons.append(nav_buttons)
    back_button = InlineKeyboardButton(text='Back', callback_data=back_callback_data)
    close_button = InlineKeyboardButton(text='Close', callback_data=CloseData().pack())
    buttons.append([back_button, close_button])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# TELEGRAM

def _fmt_tg_object(tg: Destination) -> str:
    return (f'{tg.chat.title or tg.chat.user_name or tg.chat.original_id} '
            f'{("/ " + str(tg.thread.title or tg.thread.original_id)) if tg.thread else ""}')


def _tg_objects_buttons(tgs: list[Destination]) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for tg in tgs:
        data = TgData(chat_id=tg.chat.original_id, thread_id=tg.get_thread_original_id())
        if url := tg.url:
            link_button = InlineKeyboardButton(text=_fmt_tg_object(tg), url=url)
        else:
            link_button = InlineKeyboardButton(text=_fmt_tg_object(tg), callback_data=data.pack())
        tg_button = InlineKeyboardButton(text='YouTube channels', callback_data=data.pack())
        data = StatusData(chat_id=tg.chat.original_id,
                          thread_id=tg.get_thread_original_id(),
                          status=Status(tg.chat.status))
        status_button = InlineKeyboardButton(text=Status(tg.chat.status).text(),
                                             callback_data=data.pack())
        buttons.append([link_button, status_button, tg_button])
    return buttons


def _tgs_keyboard(tgs: list[Destination],
                  prev_offset: Optional[int],
                  next_offset: Optional[int],
                  back_callback_data: str) -> InlineKeyboardMarkup:
    buttons = _tg_objects_buttons(tgs)
    nav_button = _nav_buttons(prev_offset, next_offset, Keyboard.TG_OBJECTS)
    if nav_button:
        buttons.append(nav_button)
    back_button = InlineKeyboardButton(text='Back', callback_data=back_callback_data)
    close_button = InlineKeyboardButton(text='Close', callback_data=CloseData().pack())
    buttons.append([back_button, close_button])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _calc_offsets(offset, count, length) -> tuple[Optional[int], Optional[int]]:
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if length > count else None
    return prev_offset, next_offset


# BUILD FUNCTION WITH USING DB FUNCTION

async def build_channel_keyboard(chat_id: int,
                                 thread_id: Optional[int],
                                 is_owner: bool,
                                 offset: int,
                                 count: int,
                                 tags_ids: set,
                                 back_callback_data: str,
                                 session: AsyncSession):
    rows = await get_yt_channels(chat_id, thread_id, tags_ids, offset, count + 1, session)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(rows) > count else None
    keyboard = _channel_keyboard(rows[:count], is_owner,
                                 prev_offset, next_offset,
                                 back_callback_data)
    return keyboard


async def build_tag_filter_keyboard(offset: int,
                                    count: int,
                                    checked_tag_ids: set[int],
                                    back_callback_data: str,
                                    session: AsyncSession) -> InlineKeyboardMarkup:
    tags = await get_tags(offset, count + 1, session)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(tags) > count else None
    keyboard = _tags_keyboard(tags[:count],
                              checked_tag_ids,
                              prev_offset, next_offset,
                              back_callback_data)
    return keyboard


async def build_telegram_tg_keyboard(offset: int,
                                     count: int,
                                     back_callback_data: str,
                                     session: AsyncSession):
    tgs = await get_tgs(offset, count + 1, session)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(tgs) > count else None
    keyboard = _tgs_keyboard(tgs[:count], prev_offset, next_offset, back_callback_data)
    return keyboard


async def build_attach_tags_keyboard(yt_channel_id,
                                     offset: int,
                                     count: int,
                                     back_callback_data: str,
                                     session: AsyncSession):
    tag_records = await get_yt_channel_tags(yt_channel_id, offset, count + 1, session)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(tag_records) > count else None
    keyboard = _attach_tags_keyboard(tag_records[:count], yt_channel_id,
                                     prev_offset, next_offset,
                                     back_callback_data)
    return keyboard