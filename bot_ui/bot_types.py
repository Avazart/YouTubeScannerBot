import asyncio
import copy
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import NamedTuple, Optional

import aiogram
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import StateType
from sqlalchemy.orm import sessionmaker

from auxiliary_utils import get_thread_id
from settings import Profile


@dataclass
class Data:
    keyboard_id: Optional[int] = None

    tags_offset: int = 0
    yt_channels_offset: int = 0
    tgs_offset: int = 0

    # tgs -> filter -> channel
    original_chat_id: Optional[int] = None
    original_thread_id: Optional[int] = None

    # channels -> attach tag_names -> nav_buttons
    original_channel_id: Optional[str] = None

    # tag filter -> channels -> nav buttons
    tags_ids: set[int] = field(default_factory=set)

    back_callback_data: Optional[str] = None


@dataclass
class StorageRecord:
    data: Data = field(default_factory=Data)
    state: Optional[str] = None


@dataclass(frozen=True)
class StorageKey:
    chat_id: int  # original chat_id
    thread_id: Optional[int]  # original thread_id
    user_id: int

    @staticmethod
    def from_message(m: aiogram.types.Message) -> 'StorageKey':
        return StorageKey(m.chat.id, get_thread_id(m), m.from_user.id)

    @staticmethod
    def from_callback_query(q: aiogram.types.CallbackQuery) -> 'StorageKey':
        return StorageKey(q.message.chat.id, get_thread_id(q.message), q.from_user.id)


class Storage:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._storage: defaultdict[StorageKey, StorageRecord] = defaultdict(StorageRecord)

    async def get_data(self, key: StorageKey) -> Data:
        async with self._lock:
            return copy.deepcopy(self._storage[key].data)

    async def set_data(self, key: StorageKey, data: Data) -> None:
        async with self._lock:
            self._storage[key].data = copy.deepcopy(data)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        async with self._lock:
            self._storage[key].state = state.state if isinstance(state, State) else state

    async def get_state(self, key: StorageKey) -> Optional[str]:
        async with self._lock:
            return self._storage[key].state


class BotContext(NamedTuple):
    logger: logging.Logger
    SessionMaker: sessionmaker
    profile: Profile
    storage: Storage


UNICODE_CHARS = "✅🟩🚫"


class Status(IntEnum):
    ON = 0
    OFF = 1
    BAN = 2

    def next(self) -> 'Status':
        match self:
            case self.ON:
                return self.OFF
            case self.OFF:
                return self.BAN
            case self.BAN:
                return self.ON

    def text(self) -> str:
        return f"{UNICODE_CHARS[int(self)]} {self.name}"


class Keyboard(IntEnum):
    MAIN = auto()
    TAG_FILTER = auto()
    YT_CHANNELS = auto()
    TG_OBJECTS = auto()
    ATTACH_TAGS = auto()


# CallbackData

class NavigationData(CallbackData, prefix='navigation'):
    keyboard: Keyboard


class CloseData(CallbackData, prefix='close'):
    pass


class ChannelData(CallbackData, prefix='channel'):
    id: int
    enabled: bool


class PageData(CallbackData, prefix='page'):
    offset: int
    keyboard: Keyboard


class TagFilterData(CallbackData, prefix='tag'):
    id: int


class AttachTagData(CallbackData, prefix='attach_tag'):
    channel_id: str


class YtChannelTagData(CallbackData, prefix='yt_channel_tag'):
    tag_id: int
    channel_id: str
    enabled: bool


class TgData(CallbackData, prefix='tg'):
    chat_id: int
    thread_id: Optional[int]


class StatusData(CallbackData, prefix='status'):
    chat_id: int
    thread_id: Optional[int]
    status: Status
