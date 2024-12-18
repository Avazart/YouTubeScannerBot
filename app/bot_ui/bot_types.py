from enum import IntEnum, auto
from typing import NamedTuple

from aiogram.filters.callback_data import CallbackData
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..settings import Settings

# @dataclass
# class Data:
#     keyboard_id: int | None = None
#
#     categories_offset: int = 0
#     yt_channels_offset: int = 0
#     tgs_offset: int = 0
#
#     # tgs -> filter -> channel
#     original_chat_id: int | None = None
#     original_thread_id: int | None = None
#
#     # channels -> attach tag_names -> nav_buttons
#     channel_id: int | None = None
#
#     # tag filter -> channels -> nav buttons
#     categories_ids: set[int] = field(default_factory=set)
#
#     back_callback_data: int | None = None
#
#
# @dataclass
# class StorageRecord:
#     data: Data = field(default_factory=Data)
#     state: str | None = None
#
#
# @dataclass(frozen=True)
# class StorageKey:
#     chat_id: int  # original chat_id
#     thread_id: int | None  # original thread_id
#     user_id: int
#
#     @staticmethod
#     def from_message(m: aiogram.types.Message) -> "StorageKey":
#         assert m.from_user
#         return StorageKey(m.chat.id, get_thread_id(m), m.from_user.id)
#
#     @staticmethod
#     def from_callback_query(q: aiogram.types.CallbackQuery) -> "StorageKey":
#         assert q.message and q.message.chat and q.from_user
#         return StorageKey(
#             q.message.chat.id, get_thread_id(q.message), q.from_user.id
#         )
#
#
# class Storage:
#     def __init__(self):
#         self._lock = asyncio.Lock()
#         self._storage = defaultdict(StorageRecord)
#
#     async def get_data(self, key: StorageKey) -> Data:
#         async with self._lock:
#             return copy.deepcopy(self._storage[key].data)
#
#     async def set_data(self, key: StorageKey, data: Data) -> None:
#         async with self._lock:
#             self._storage[key].data = copy.deepcopy(data)
#
#     async def set_state(
#         self, key: StorageKey, state: StateType = None
#     ) -> None:
#         async with self._lock:
#             if isinstance(state, State):
#                 self._storage[key].state = state.state
#             else:
#                 self._storage[key].state = None
#
#     async def get_state(self, key: StorageKey) -> str | None:
#         async with self._lock:
#             return self._storage[key].state


class BotContext(NamedTuple):
    settings: Settings
    # storage: Storage
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


class Keyboard(IntEnum):
    MAIN = auto()
    CATEGORY = auto()
    YT_CHANNELS = auto()
    TG_OBJECTS = auto()
    ATTACH_CATEGORIES = auto()


# CallbackData


class NavData(CallbackData, prefix="navigation"):
    keyboard: Keyboard


class CloseData(CallbackData, prefix="close"):
    pass


class ChannelData(CallbackData, prefix="channel"):
    id: int
    enabled: bool


class PageData(CallbackData, prefix="page"):
    offset: int
    keyboard: Keyboard


class CategoryFilterData(CallbackData, prefix="category"):
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
