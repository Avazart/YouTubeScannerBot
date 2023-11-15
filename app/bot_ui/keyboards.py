from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from .bot_types import (
    PageData,
    ChannelData,
    AttachCategoryData,
    CategoryFilterData,
    YTChannelCategoryData,
    TgData,
    StatusData,
    Keyboard,
    NavData,
    CloseData,
)
from ..auxiliary_utils import batched_evenly
from ..database.models import (
    YouTubeChannel,
    Category,
    Status,
    YTChannelCategory,
)
from ..database.utils import (
    Destination,
    get_yt_channels,
    get_categories,
    get_tgs,
    get_yt_channel_categories,
)
from ..settings import KEYBOARD_COLUMN_COUNT


def _nav_buttons(
    prev_offset: int | None,
    next_offset: int | None,
    keyboard: Keyboard,
) -> list[InlineKeyboardButton]:
    nav_buttons = []
    if prev_offset is not None:
        prev_data = PageData(keyboard=keyboard, offset=prev_offset)
        prev_button = InlineKeyboardButton(
            text="⬅  Prev",
            callback_data=prev_data.pack(),
        )
        nav_buttons.append(prev_button)
    if next_offset is not None:
        next_data = PageData(keyboard=keyboard, offset=next_offset)
        next_button = InlineKeyboardButton(
            text="Next  ➡",
            callback_data=next_data.pack(),
        )
        nav_buttons.append(next_button)
    return nav_buttons


# MAIN


def build_main_keyboard(is_owner: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="YouTube channels",
                callback_data=NavData(
                    keyboard=Keyboard.CATEGORY_FILTER
                ).pack(),
            )
        ]
    ]
    if is_owner:
        button = InlineKeyboardButton(
            text="Telegram chats and threads",
            callback_data=NavData(keyboard=Keyboard.TG_OBJECTS).pack(),
        )
        buttons.append([button])

    buttons.append(
        [
            InlineKeyboardButton(
                text="Close",
                callback_data=CloseData().pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# CHANNEL


def _channel_buttons(
    rows: list[tuple[YouTubeChannel, bool]],
    is_owner: bool,
) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for channel, enabled in rows:
        text = f'{"✅" if enabled else " "} {channel.title}'
        assert channel.id is not None
        data = ChannelData(id=channel.id, enabled=enabled)
        check_button = InlineKeyboardButton(
            text=text,
            callback_data=data.pack(),
        )
        link_button = InlineKeyboardButton(
            text="Open in browser",
            url=channel.canonical_url,
        )
        buttons.append([check_button, link_button])
        if is_owner:
            data2 = AttachCategoryData(channel_id=channel.id)
            categories_button = InlineKeyboardButton(
                text="Categories",
                callback_data=data2.pack(),
            )
            buttons[-1].append(categories_button)
    return buttons


def _channel_keyboard(
    rows: list[tuple[YouTubeChannel, bool]],
    is_owner: bool,
    prev_offset: int | None,
    next_offset: int | None,
    back_callback_data: str | None,
) -> InlineKeyboardMarkup:
    buttons = _channel_buttons(rows, is_owner)
    if nav_buttons := _nav_buttons(
        prev_offset,
        next_offset,
        Keyboard.YT_CHANNELS,
    ):
        buttons.append(nav_buttons)
    back_button = InlineKeyboardButton(
        text="Back",
        callback_data=back_callback_data,
    )
    close_button = InlineKeyboardButton(
        text="Close",
        callback_data=CloseData().pack(),
    )
    buttons.append([back_button, close_button])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# СATEGORIES


def _category_buttons(
    categories: list[Category],
    checked_category_ids: set[int],
) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for row in batched_evenly(categories, KEYBOARD_COLUMN_COUNT):
        row_buttons = []
        for category in row:
            checked = category.id in checked_category_ids
            text = f'{"✅" if checked else "🟩"} {category.name}'
            data = CategoryFilterData(id=category.id)
            category_button = InlineKeyboardButton(
                text=text,
                callback_data=data.pack(),
            )
            row_buttons.append(category_button)
        buttons.append(row_buttons)
    return buttons


def _categories_keyboard(
    categories: list[Category],
    checked_category_ids: set[int],
    prev_offset: int | None,
    next_offset: int | None,
    back_callback_data: str | None,
) -> InlineKeyboardMarkup:
    buttons = _category_buttons(categories, checked_category_ids)
    if nav_buttons := _nav_buttons(
        prev_offset,
        next_offset,
        Keyboard.CATEGORY_FILTER,
    ):
        buttons.append(nav_buttons)
    back_button = InlineKeyboardButton(
        text="Back",
        callback_data=back_callback_data,
    )
    close_button = InlineKeyboardButton(
        text="Close",
        callback_data=CloseData().pack(),
    )
    apply_button = InlineKeyboardButton(
        text="Apply",
        callback_data=NavData(keyboard=Keyboard.YT_CHANNELS).pack(),
    )
    buttons.append([back_button, close_button, apply_button])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ATTACH CATEGORIES


def _attach_categories_buttons(
    category_records: list[tuple[YTChannelCategory, bool]],
    yt_channel_id: int,
) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for row in batched_evenly(category_records, KEYBOARD_COLUMN_COUNT):
        row_buttons = []
        for category, enable in row:
            text = f'{"✅" if enable else " "} {category.name}'
            data = YTChannelCategoryData(
                category_id=category.id,
                channel_id=yt_channel_id,
                enabled=enable,
            )
            category_button = InlineKeyboardButton(
                text=text,
                callback_data=data.pack(),
            )
            row_buttons.append(category_button)
        buttons.append(row_buttons)
    return buttons


def _attach_categories_keyboard(
    category_records: list[tuple[YTChannelCategory, bool]],
    yt_channel_id: int,
    prev_offset: int | None,
    next_offset: int | None,
    back_callback_data: str | None,
) -> InlineKeyboardMarkup:
    buttons = _attach_categories_buttons(category_records, yt_channel_id)
    if nav_buttons := _nav_buttons(
        prev_offset,
        next_offset,
        Keyboard.ATTACH_CATEGORIES,
    ):
        buttons.append(nav_buttons)
    close_button = InlineKeyboardButton(
        text="Close",
        callback_data=CloseData().pack(),
    )
    if back_callback_data:
        back_button = InlineKeyboardButton(
            text="Back",
            callback_data=back_callback_data,
        )
        buttons.append([back_button, close_button])
    else:
        buttons.append([close_button])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# TELEGRAM


def _fmt_tg_object(tg: Destination) -> str:
    title = tg.chat.title or tg.chat.user_name or tg.chat.original_id
    if tg.thread:
        thread = " / " + str(tg.thread.title or tg.thread.original_id)
    else:
        thread = ""
    return f"{title}{thread}"


def _tg_objects_buttons(
    tgs: list[Destination],
) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for tg in tgs:
        data = TgData(
            chat_id=tg.chat.original_id,
            thread_id=tg.get_thread_original_id(),
        )
        if url := tg.url:
            link_button = InlineKeyboardButton(
                text=_fmt_tg_object(tg),
                url=url,
            )
        else:
            link_button = InlineKeyboardButton(
                text=_fmt_tg_object(tg),
                callback_data=data.pack(),
            )
        tg_button = InlineKeyboardButton(
            text="YouTube channels",
            callback_data=data.pack(),
        )
        data2 = StatusData(
            chat_id=tg.chat.original_id,
            thread_id=tg.get_thread_original_id(),
            status=Status(tg.chat.status),
        )
        status_button = InlineKeyboardButton(
            text=Status(tg.chat.status).text(),
            callback_data=data2.pack(),
        )
        buttons.append([link_button, status_button, tg_button])
    return buttons


def _tgs_keyboard(
    tgs: list[Destination],
    prev_offset: int | None,
    next_offset: int | None,
    back_callback_data: str | None,
) -> InlineKeyboardMarkup:
    buttons = _tg_objects_buttons(tgs)
    nav_button = _nav_buttons(prev_offset, next_offset, Keyboard.TG_OBJECTS)
    if nav_button:
        buttons.append(nav_button)
    back_button = InlineKeyboardButton(
        text="Back",
        callback_data=back_callback_data,
    )
    close_button = InlineKeyboardButton(
        text="Close",
        callback_data=CloseData().pack(),
    )
    buttons.append([back_button, close_button])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _calc_offsets(offset, count, length) -> tuple[int | None, int | None]:
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if length > count else None
    return prev_offset, next_offset


# BUILD FUNCTION WITH USING DB FUNCTION


async def build_channel_keyboard(
    chat_id: int,
    thread_id: int | None,
    is_owner: bool,
    offset: int,
    count: int,
    categories_ids: set,
    back_callback_data: str | None,
    session: AsyncSession,
):
    rows = await get_yt_channels(
        chat_id,
        thread_id,
        categories_ids,
        offset,
        count + 1,
        session,
    )
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(rows) > count else None
    keyboard = _channel_keyboard(
        rows[:count],
        is_owner,
        prev_offset,
        next_offset,
        back_callback_data,
    )
    return keyboard


async def build_category_filter_keyboard(
    offset: int,
    count: int,
    checked_category_ids: set[int],
    back_callback_data: str | None,
    session: AsyncSession,
) -> InlineKeyboardMarkup:
    categories = await get_categories(offset, count + 1, session)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(categories) > count else None
    keyboard = _categories_keyboard(
        categories[:count],
        checked_category_ids,
        prev_offset,
        next_offset,
        back_callback_data,
    )
    return keyboard


async def build_telegram_tg_keyboard(
    offset: int,
    count: int,
    back_callback_data: str | None,
    session: AsyncSession,
):
    tgs = await get_tgs(offset, count + 1, session)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(tgs) > count else None
    keyboard = _tgs_keyboard(
        tgs[:count],
        prev_offset,
        next_offset,
        back_callback_data,
    )
    return keyboard


async def build_attach_categories_keyboard(
    yt_channel_id: int,
    offset: int,
    count: int,
    back_callback_data: str | None,
    session: AsyncSession,
):
    category_records = await get_yt_channel_categories(
        yt_channel_id,
        offset,
        count + 1,
        session,
    )
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(category_records) > count else None
    keyboard = _attach_categories_keyboard(
        category_records[:count],
        yt_channel_id,
        prev_offset,
        next_offset,
        back_callback_data,
    )
    return keyboard
