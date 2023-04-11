from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import aiogram
from sqlalchemy import (
    DateTime,
    String,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    BigInteger
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from auxiliary_utils import make_repr
from bot_ui.bot_types import Status

YT_VIDEO_URL_FMT = 'https://www.youtube.com/watch?v={id}'
YT_CHANNEL_URL_FMT = 'https://www.youtube.com/channel/{id}'
YT_CHANNEL_CANONICAL_URL_FMT = 'https://www.youtube.com{base_url}'
TG_URL_FMT = 'https://t.me/{user_name}'


class Base(DeclarativeBase):
    __abstract__ = True


class YouTubeChannel(Base):
    __tablename__ = "YouTubeChannels"

    id: Mapped[int | None] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    original_id: Mapped[str] = mapped_column(
        String,
        unique=True,
    )
    canonical_base_url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)

    @property
    def url(self) -> str:
        return YT_CHANNEL_URL_FMT.format(id=self.original_id)

    @property
    def canonical_url(self) -> str:
        return YT_CHANNEL_CANONICAL_URL_FMT.format(
            base_url=self.canonical_base_url
        )

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash(self.original_id)

    def __eq__(self, other):
        return self.original_id == other.original_id


class TelegramChat(Base):
    __tablename__ = "TelegramChats"

    original_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )
    type: Mapped[str] = mapped_column(
        String,
        default=None
    )
    title: Mapped[str] = mapped_column(
        String,
        default=None,
        nullable=True
    )
    user_name: Mapped[str] = mapped_column(
        String,
        default=None
    )
    first_name: Mapped[str] = mapped_column(
        String,
        default=None,
        nullable=True
    )
    last_name: Mapped[str] = mapped_column(
        String,
        default=None,
        nullable=True
    )
    is_creator: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=True
    )
    status: Mapped[int] = mapped_column(
        default=int(Status.ON),
    )

    @property
    def url(self) -> Optional[str]:
        return (TG_URL_FMT.format(user_name=self.user_name)
                if self.user_name
                else None)

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

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    original_id: Mapped[int] = mapped_column(
        BigInteger,
    )
    original_chat_id: Mapped[int] = mapped_column(
        ForeignKey(TelegramChat.original_id,
                   ondelete="CASCADE",
                   onupdate='CASCADE'),
    )

    title: Mapped[str] = mapped_column(
        String,
        default=None,
        nullable=True
    )

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
        return ((self.chat, self.thread) ==
                (other.chat, other.thread))


class Forwarding(Base):
    __tablename__ = "Forwarding"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    youtube_channel_id: Mapped[int] = mapped_column(
        ForeignKey(YouTubeChannel.id,
                   ondelete="CASCADE",
                   onupdate='CASCADE'),
    )
    telegram_chat_id: Mapped[int] = mapped_column(
        ForeignKey(TelegramChat.original_id,
                   ondelete="CASCADE",
                   onupdate='CASCADE'),
    )
    telegram_thread_id: Mapped[int] = mapped_column(
        ForeignKey(TelegramThread.id,
                   ondelete="CASCADE",
                   onupdate='CASCADE'),
        nullable=True
    )

    __table_args__ = (
        UniqueConstraint('youtube_channel_id',
                         'telegram_chat_id',
                         'telegram_thread_id',
                         name='unique_forwarding'),
    )

    def __repr__(self):
        return make_repr(self)


class YouTubeVideo(Base):
    __tablename__ = "YouTubeVideos"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    original_id: Mapped[str] = mapped_column(
        String,
        unique=True,
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey(YouTubeChannel.id,
                   ondelete='CASCADE',
                   onupdate='CASCADE'),
        default=None
    )
    title: Mapped[str] = mapped_column(
        String,
        default=None,
        nullable=True
    )
    style: Mapped[str] = mapped_column(
        String,
        default=None,
        nullable=True
    )
    time_ago: Mapped[str] = mapped_column(
        String,
        default=None,
        nullable=True
    )
    scan_time: Mapped[datetime] = mapped_column(
        DateTime,
    )
    creation_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=None,
        nullable=True
    )

    live_24_7: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    url = property(lambda self:
                   YT_VIDEO_URL_FMT.format(id=self.original_id))

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash(self.original_id)

    def __eq__(self, other):
        return self.original_id == other.original_id


class Tag(Base):
    __tablename__ = "Tags"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String,
        unique=True,
    )
    order: Mapped[int] = mapped_column(
        autoincrement=True
    )

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


class YouTubeChannelTag(Base):
    __tablename__ = "YouTubeChannelTags"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey(Tag.id,
                   ondelete="CASCADE",
                   onupdate='CASCADE')
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey(YouTubeChannel.id,
                   ondelete="CASCADE",
                   onupdate='CASCADE')
    )
    __table_args__ = (
        UniqueConstraint('tag_id',
                         'channel_id',
                         name='unique_yt_tag'),
    )

    def __repr__(self):
        return make_repr(self)

    def __hash__(self):
        return hash((self.tag_id, self.channel_id))

    def __eq__(self, other):
        return ((self.tag_id, self.channel_id) ==
                (other.tag_id, other.channel_id))
