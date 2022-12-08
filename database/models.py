from dataclasses import dataclass
from typing import Optional

import aiogram
from sqlalchemy import Column, Integer, DateTime, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base

from auxiliary_utils import make_repr
from bot_ui.bot_types import Status

YT_VIDEO_URL_FMT = 'https://www.youtube.com/watch?v={id}'
YT_CHANNEL_URL_FMT = 'https://www.youtube.com/channel/{id}'
YT_CHANNEL_CANONICAL_URL_FMT = 'https://www.youtube.com{base_url}'
TG_URL_FMT = 'https://t.me/{user_name}'

Base = declarative_base()


class YouTubeChannel(Base):
    __tablename__ = "YouTubeChannels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_id = Column(String, unique=True, nullable=False)
    canonical_base_url = Column(String)
    title = Column(String)

    @property
    def url(self) -> str:
        return YT_CHANNEL_URL_FMT.format(id=self.original_id)

    @property
    def canonical_url(self) -> str:
        return YT_CHANNEL_CANONICAL_URL_FMT.format(base_url=self.canonical_base_url)

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash(self.original_id)

    def __eq__(self, other):
        return self.original_id == other.original_id


class TelegramChat(Base):
    __tablename__ = "TelegramChats"

    original_id = Column(Integer, primary_key=True)
    type = Column(String, default=None)
    title = Column(String, default=None)

    user_name = Column(String, default=None)
    first_name = Column(String, default=None)
    last_name = Column(String, default=None)
    is_creator = Column(Boolean, default=False)
    # description

    status = Column(Integer, default=Status.ON)

    @property
    def url(self) -> Optional[str]:
        return TG_URL_FMT.format(user_name=self.user_name) if self.user_name else None

    @staticmethod
    def from_aiogram_chat(chat: aiogram.types.Chat) -> 'TelegramChat':
        return TelegramChat(original_id=chat.id,
                            type=chat.type,
                            title=chat.title,
                            user_name=chat.username,
                            first_name=chat.first_name,
                            last_name=chat.last_name,
                            is_creator=None,
                            status=Status.ON)

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash(self.original_id)

    def __eq__(self, other):
        return self.original_id == other.original_id


class TelegramThread(Base):
    __tablename__ = "TelegramThreads"

    id = Column(Integer, primary_key=True, autoincrement=True)

    original_id = Column(Integer, nullable=False)
    original_chat_id = Column(ForeignKey(TelegramChat.original_id,
                                         ondelete="CASCADE",
                                         onupdate='CASCADE'),
                              nullable=False)

    title = Column(String, default=None)

    __table_args__ = (UniqueConstraint('original_id',
                                       'original_chat_id',
                                       name='unique_thread'),)

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash((self.original_chat_id, self.original_id))

    def __eq__(self, other):
        return (self.original_chat_id, self.original_id) == \
               (other.chat_id, other.original_id)


@dataclass
class Destination:
    chat: TelegramChat
    thread: Optional[TelegramThread]

    @property
    def url(self) -> Optional[str]:
        if chart_url := self.chat.url:
            if self.thread:
                return f'{chart_url}/{self.thread.original_id}'
            else:
                return chart_url
        return None

    def get_thread_id(self) -> Optional[int]:
        return self.thread.id if self.thread else None

    def get_thread_original_id(self) -> Optional[int]:
        return self.thread.original_id if self.thread else None

    def __hash__(self):
        return hash((self.chat, self.thread))

    def __eq__(self, other):
        return (self.chat, self.thread) == (other.chat, other.thread)


class Forwarding(Base):
    __tablename__ = "Forwarding"

    id = Column(Integer, primary_key=True, autoincrement=True)

    youtube_channel_id = \
        Column(ForeignKey(YouTubeChannel.id, ondelete="CASCADE", onupdate='CASCADE'), nullable=False)

    telegram_chat_id = \
        Column(ForeignKey(TelegramChat.original_id, ondelete="CASCADE", onupdate='CASCADE'), nullable=False)

    telegram_thread_id = \
        Column(ForeignKey(TelegramThread.id, ondelete="CASCADE", onupdate='CASCADE'), nullable=True)

    __table_args__ = (UniqueConstraint('youtube_channel_id',
                                       'telegram_chat_id',
                                       'telegram_thread_id',
                                       name='unique_forwarding'),)

    def __repr__(self):
        return make_repr(self)


class YouTubeVideo(Base):
    __tablename__ = "YouTubeVideos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_id = Column(String, unique=True, nullable=False)
    channel_id = Column(ForeignKey(YouTubeChannel.id, ondelete='CASCADE', onupdate='CASCADE'),
                        default=None)

    title = Column(String, default=None)
    style = Column(String, default=None)

    time_ago = Column(String, default=None)
    scan_time = Column(DateTime)
    creation_time = Column(DateTime, default=None)

    live_24_7 = Column(Boolean, default=False)

    url = property(lambda self: YT_VIDEO_URL_FMT.format(id=self.original_id))

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash(self.original_id)

    def __eq__(self, other):
        return self.original_id == other.original_id


class Tag(Base):
    __tablename__ = "Tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    order = Column(Integer, autoincrement=True)

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


class YouTubeChannelTag(Base):
    __tablename__ = "YouTubeChannelTags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag_id = Column(ForeignKey(Tag.id, ondelete="CASCADE", onupdate='CASCADE'))
    channel_id = Column(ForeignKey(YouTubeChannel.id, ondelete="CASCADE", onupdate='CASCADE'))

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash((self.tag_id, self.channel_id))

    def __eq__(self, other):
        return (self.tag_id, self.channel_id) == (other.tag_id, other.channel_id)
