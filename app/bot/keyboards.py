import logging
from enum import StrEnum

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from ..auxiliary_utils import batched_evenly
from ..constants import KEYBOARD_COLUMN_COUNT
from ..database.models import Category, Destination, Status, YouTubeChannel
from ..database.services import (
    CategoryService,
    TelegramService,
    YTChannelCategoryService,
    YTChannelService,
)
from .bot_types import (
    AttachCategoryData,
    BackData,
    CategoriesMenuData,
    CategoryData,
    ChannelData,
    ChannelsMenuData,
    CloseData,
    PageData,
    StatusData,
    TelegramsMenuData,
    TgData,
    VideoLinksData,
    YTChannelCategoryData,
)

logger = logging.getLogger(__name__)


class Emoji(StrEnum):
    HEAVY_MULTIPLICATION_X = "✖"
    BACK_WITH_LEFTWARDS_ARROW_ABOVE = "🔙"
    BLACK_RIGHTWARDS_ARROW = "➡"
    LEFTWARDS_BLACK_ARROW = "⬅"
    HEAVY_CHECK_MARK = "✔️"
    BLACK_DIAMOND_SUIT = "♦️"
    PUSHPIN = "📌"
    BULLSEYE = "⦿"
    WHITE_HEAVY_CHECK_MARK = "✅"
    LARGE_GREEN_SQUARE = "🟩"


def _close_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"{Emoji.HEAVY_MULTIPLICATION_X} Close",
        callback_data=CloseData().pack(),
    )


def _back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"{Emoji.BACK_WITH_LEFTWARDS_ARROW_ABOVE} Back",
        callback_data=BackData().pack(),
    )


def _next_button(offset: int) -> InlineKeyboardButton:
    next_data = PageData(offset=offset)
    return InlineKeyboardButton(
        text=f"Next {Emoji.BLACK_RIGHTWARDS_ARROW}",
        callback_data=next_data.pack(),
    )


def _prev_button(offset: int) -> InlineKeyboardButton:
    prev_data = PageData(offset=offset)
    return InlineKeyboardButton(
        text=f"{Emoji.LEFTWARDS_BLACK_ARROW} Prev",
        callback_data=prev_data.pack(),
    )


def _apply_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"{Emoji.HEAVY_CHECK_MARK} Apply",
        callback_data=ChannelsMenuData().pack(),
    )


def _nav_buttons(
    prev_offset: int | None,
    next_offset: int | None,
) -> list[InlineKeyboardButton]:
    nav_buttons = []
    if prev_offset is not None:
        nav_buttons.append(_prev_button(prev_offset))
    if next_offset is not None:
        nav_buttons.append(_next_button(next_offset))
    return nav_buttons


# MAIN


def build_main_keyboard(is_owner: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{Emoji.BLACK_DIAMOND_SUIT} YouTube channels",
                callback_data=CategoriesMenuData().pack(),
            )
        ]
    ]
    if is_owner:
        button = InlineKeyboardButton(
            text=f"{Emoji.BLACK_DIAMOND_SUIT} Telegram chats and threads",
            callback_data=TelegramsMenuData().pack(),
        )
        buttons.append([button])

    buttons.append([_close_button()])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# CHANNEL


def _channel_buttons(
    rows: list[tuple[YouTubeChannel, bool]],
    is_owner: bool,
) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for channel, enabled in rows:
        emoji = (
            Emoji.WHITE_HEAVY_CHECK_MARK
            if enabled
            else Emoji.LARGE_GREEN_SQUARE
        )
        text = f"{emoji} {channel.title}"
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
                text=f"{Emoji.BLACK_DIAMOND_SUIT} Categories",
                callback_data=data2.pack(),
            )
            buttons[-1].append(categories_button)
    return buttons


def _channel_keyboard(
    rows: list[tuple[YouTubeChannel, bool]],
    is_owner: bool,
    prev_offset: int | None,
    next_offset: int | None,
) -> InlineKeyboardMarkup:
    buttons = _channel_buttons(rows, is_owner)
    if nav_buttons := _nav_buttons(prev_offset, next_offset):
        buttons.append(nav_buttons)
    buttons.append([_back_button(), _close_button()])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# СATEGORIES


def _category_buttons(
    categories: list[Category],
    selected: set[int],
) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for row in batched_evenly(categories, KEYBOARD_COLUMN_COUNT):
        row_buttons = []
        for category in row:
            checked = category.id in selected
            emoji = (
                Emoji.WHITE_HEAVY_CHECK_MARK
                if checked
                else Emoji.LARGE_GREEN_SQUARE
            )
            text = f"{emoji} {category.name}"
            data = CategoryData(id=category.id)
            category_button = InlineKeyboardButton(
                text=text,
                callback_data=data.pack(),
            )
            row_buttons.append(category_button)
        buttons.append(row_buttons)
    return buttons


def _categories_keyboard(
    categories: list[Category],
    selected: set[int],
    prev_offset: int | None,
    next_offset: int | None,
) -> InlineKeyboardMarkup:
    buttons = _category_buttons(categories, selected)
    if nav_buttons := _nav_buttons(prev_offset, next_offset):
        buttons.append(nav_buttons)

    buttons.append([_back_button(), _close_button(), _apply_button()])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ATTACH CATEGORIES


def _category_button(
    category: Category,
    channel_id: int,
    enabled: bool,
    attach: bool = False,
) -> InlineKeyboardButton:
    if attach:
        emoji = Emoji.PUSHPIN if enabled else Emoji.BULLSEYE
    else:
        emoji = (
            Emoji.WHITE_HEAVY_CHECK_MARK
            if enabled
            else Emoji.LARGE_GREEN_SQUARE
        )
    text = f"{emoji} {category.name}"
    data = YTChannelCategoryData(
        category_id=category.id, channel_id=channel_id, enabled=enabled
    )
    return InlineKeyboardButton(text=text, callback_data=data.pack())


def _attach_categories_buttons(
    category_records: list[tuple[Category, bool]],
    channel_id: int,
) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for row in batched_evenly(category_records, KEYBOARD_COLUMN_COUNT):
        row_buttons = []
        for category, enabled in row:
            row_buttons.append(
                _category_button(category, channel_id, enabled, attach=True)
            )
        buttons.append(row_buttons)
    return buttons


def _attach_categories_keyboard(
    category_records: list[tuple[Category, bool]],
    yt_channel_id: int,
    prev_offset: int | None,
    next_offset: int | None,
) -> InlineKeyboardMarkup:
    buttons = _attach_categories_buttons(category_records, yt_channel_id)
    if nav_buttons := _nav_buttons(prev_offset, next_offset):
        buttons.append(nav_buttons)

    buttons.append([_back_button(), _close_button()])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# TELEGRAM


def _fmt_tg_object(tg: Destination) -> str:
    title = tg.chat.title or tg.chat.user_name or tg.chat.original_id
    if tg.thread:
        thread = " / " + str(tg.thread.title or tg.thread.original_id)
    else:
        thread = ""
    return f"{title}{thread}"


def _status_button(tg: Destination) -> InlineKeyboardButton:
    status_data = StatusData(
        chat_id=tg.chat.original_id,
        thread_id=tg.get_thread_original_id(),
        status=Status(tg.chat.status),
    )
    return InlineKeyboardButton(
        text=Status(tg.chat.status).text(),
        callback_data=status_data.pack(),
    )


def _tg_objects_buttons(
    tgs: list[Destination],
) -> list[list[InlineKeyboardButton]]:
    buttons = []
    for tg in tgs:
        tg_data = TgData(
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
                callback_data=tg_data.pack(),
            )
        tg_button = InlineKeyboardButton(
            text=f"{Emoji.BLACK_DIAMOND_SUIT} YouTube channels "
            f"({tg.chat.original_id}/{tg.get_thread_original_id()})",
            callback_data=tg_data.pack(),
        )
        buttons.append([link_button, _status_button(tg), tg_button])
    return buttons


def _tgs_keyboard(
    tgs: list[Destination],
    prev_offset: int | None,
    next_offset: int | None,
) -> InlineKeyboardMarkup:
    buttons = _tg_objects_buttons(tgs)
    nav_button = _nav_buttons(prev_offset, next_offset)
    if nav_button:
        buttons.append(nav_button)

    buttons.append([_back_button(), _close_button()])
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
    session: AsyncSession,
) -> InlineKeyboardMarkup:
    service = YTChannelService(session)
    rows = await service.get_all(
        chat_id, thread_id, categories_ids, offset, count + 1
    )
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(rows) > count else None
    keyboard = _channel_keyboard(
        rows[:count],
        is_owner,
        prev_offset,
        next_offset,
    )
    return keyboard


async def build_category_filter_keyboard(
    offset: int,
    count: int,
    selected_categories: set[int],
    session: AsyncSession,
) -> InlineKeyboardMarkup:
    service = CategoryService(session)
    categories = await service.get_all(offset, count + 1)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(categories) > count else None
    keyboard = _categories_keyboard(
        categories[:count],
        selected_categories,
        prev_offset,
        next_offset,
    )
    return keyboard


async def build_telegram_tg_keyboard(
    offset: int,
    count: int,
    session: AsyncSession,
) -> InlineKeyboardMarkup:
    service = TelegramService(session)
    tgs = await service.get_all(offset, count + 1)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(tgs) > count else None
    keyboard = _tgs_keyboard(tgs[:count], prev_offset, next_offset)
    return keyboard


async def build_attach_categories_keyboard(
    channel_id: int,
    offset: int,
    count: int,
    session: AsyncSession,
) -> InlineKeyboardMarkup:
    service = YTChannelCategoryService(session)
    category_records = await service.get_all(channel_id, offset, count + 1)
    prev_offset = offset - count if offset > 0 else None
    next_offset = offset + count if len(category_records) > count else None
    keyboard = _attach_categories_keyboard(
        category_records[:count],
        channel_id,
        prev_offset,
        next_offset,
    )
    return keyboard


def video_links_keyboard(selected: int, total: int) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [[]]
    for n in range(1, total + 1):
        if n != selected:
            button = InlineKeyboardButton(
                text=str(n), callback_data=VideoLinksData(number=n).pack()
            )
            buttons[0].append(button)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
