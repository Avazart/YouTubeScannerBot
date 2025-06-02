"""
    MAIN   + -> CATEGORIES -> CHANNELS
           |       ^
           |       |
           + -> TELEGRAMS
"""


import logging
from collections.abc import Sequence
from enum import IntEnum
from typing import NamedTuple

from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..settings import Settings

logger = logging.getLogger(__name__)


class Menu(StatesGroup):
    MAIN = State()
    CATEGORIES = State()
    CHANNELS = State()
    TELEGRAMS = State()
    ATTACH_CATEGORIES = State()


class StateHistory:
    def __init__(self, lst: list[State] | None = None):
        self._lst: list[State] = lst if lst else []
        logger.debug("Load %s", self)

    def to_list(self) -> list[State]:
        logger.debug("Dump %s", self)
        return self._lst

    def __len__(self):
        return len(self._lst)

    def __bool__(self):
        return bool(self._lst)

    def __getitem__(self, item):
        return self._lst[item]

    def __repr__(self):
        return f"History({self._lst})"

    def append(self, value: State) -> None:
        if self._lst:
            if self._lst[-1] != value:
                self._lst.append(value)
        else:
            self._lst.append(value)
        logger.debug("History.append value=%s %s", value, self)

    def back(self) -> State | None:
        return self._lst[-1] if self._lst else None

    def pop(self) -> State | None:
        value = self._lst.pop() if self._lst else None
        logger.debug("History.pop value=%s %s", value, self)
        return value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type,
        _handler: GetCoreSchemaHandler,
    ):
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.list_schema(core_schema.str_schema()),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: [s.state for s in v._lst]
            ),
        )

    @classmethod
    def _validate(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, Sequence) and all(isinstance(v, str) for v in value):
            result = []
            for raw in value:
                if ":" in raw:
                    *group_parts, state_name = raw.split(":")
                    group_name = ":".join(group_parts)
                    result.append(State(state=state_name, group_name=group_name))
                else:
                    result.append(State(state=raw))
            return cls(result)
        raise TypeError("Expected list[str] or History")


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
