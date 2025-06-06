"""
MAIN   + -> CATEGORIES -> CHANNELS -> ATTACH CATEGORIES
       |       ^
       |       |
       + -> TELEGRAMS
"""

import logging
from enum import IntEnum
from typing import NamedTuple

from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..settings import Settings

logger = logging.getLogger(__name__)


class Menu(StatesGroup):
    MAIN = State()
    CATEGORIES = State()
    CHANNELS = State()
    TELEGRAMS = State()
    ATTACH_CATEGORIES = State()


class BotContext(NamedTuple):
    settings: Settings
    session_maker: async_sessionmaker


UNICODE_CHARS = "✅🟩🚫"


class Status(IntEnum):
    ON = 0
    OFF = 1
    BAN = 2

    def next(self) -> "Status":
        match self:
            case Status.ON:
                return Status.OFF
            case self.OFF:
                return Status.BAN
            case self.BAN:
                return Status.ON
            case _:
                raise ValueError()

    def text(self) -> str:
        return f"{UNICODE_CHARS[int(self)]} {self.name}"


# CallbackData


class CategoriesMenuData(CallbackData, prefix="categories"):
    pass


class ChannelsMenuData(CallbackData, prefix="channels"):
    pass


class TelegramsMenuData(CallbackData, prefix="telegrams"):
    pass


class NavData(CallbackData, prefix="navigation"):
    pass


class CloseData(CallbackData, prefix="close"):
    pass


class BackData(CallbackData, prefix="back"):
    pass


class ChannelData(CallbackData, prefix="channel"):
    id: int
    enabled: bool


class PageData(CallbackData, prefix="page"):
    offset: int


class CategoryData(CallbackData, prefix="category"):
    id: int


class AttachCategoryData(CallbackData, prefix="attach_category"):
    channel_id: int  # id in database


class YTChannelCategoryData(CallbackData, prefix="yt_channel_category"):
    category_id: int
    channel_id: int
    enabled: bool


class TgData(CallbackData, prefix="tg"):
    chat_id: int
    thread_id: int | None


class StatusData(CallbackData, prefix="status"):
    chat_id: int
    thread_id: int | None
    status: Status


class VideoLinksData(CallbackData, prefix="video_links"):
    number: int
