from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiogram
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from ..bot_ui.bot_types import Status

YT_VIDEO_URL_FMT = "https://www.youtube.com/watch?v={id}"
YT_CHANNEL_URL_FMT = "https://www.youtube.com/channel/{id}"
YT_CHANNEL_CANONICAL_URL_FMT = "https://www.youtube.com{base_url}"
TG_URL_FMT = "https://t.me/{user_name}"


class Base(DeclarativeBase):
    __abstract__ = True


class YouTubeChannel(Base):
    __tablename__ = "YouTubeChannels"

    id: Mapped[int] = mapped_column(
        init=False, primary_key=True, autoincrement=True
    )
    original_id: Mapped[str] = mapped_column(unique=True)
    canonical_base_url: Mapped[str] = mapped_column()
    title: Mapped[str] = mapped_column()

    @property
    def url(self) -> str:
        return YT_CHANNEL_URL_FMT.format(id=self.original_id)

    @property
    def canonical_url(self) -> str:
        return YT_CHANNEL_CANONICAL_URL_FMT.format(
            base_url=self.canonical_base_url
        )

    def __hash__(self):
        return hash(self.original_id)

    def __eq__(self, other):
        return self.original_id == other.original_id


class TelegramChat(Base):
    __tablename__ = "TelegramChats"

    original_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    type: Mapped[str] = mapped_column(default=None)
    title: Mapped[str | None] = mapped_column(default=None)
    user_name: Mapped[str] = mapped_column(default=None)
    first_name: Mapped[str | None] = mapped_column(default=None)
    last_name: Mapped[str | None] = mapped_column(default=None)
    is_creator: Mapped[bool | None] = mapped_column(default=False)
    status: Mapped[int] = mapped_column(default=int(Status.ON))

    @property
    def url(self) -> str | None:
        return (
            TG_URL_FMT.format(user_name=self.user_name)
            if self.user_name
            else None
        )

    @staticmethod
    def from_aiogram_chat(chat: aiogram.types.Chat) -> "TelegramChat":
        return TelegramChat(
            original_id=chat.id,
            type=chat.type,
            title=chat.title or "",
            user_name=chat.username or "",
            first_name=chat.first_name or "",
            last_name=chat.last_name or "",
            is_creator=False,
            status=Status.ON,
        )

    def __hash__(self):
        return hash(self.original_id)

    def __eq__(self, other):
        return self.original_id == other.original_id


class TelegramThread(Base):
    __tablename__ = "TelegramThreads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    original_id: Mapped[int] = mapped_column(BigInteger)
    original_chat_id: Mapped[int] = mapped_column(
        ForeignKey(
            TelegramChat.original_id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    title: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        UniqueConstraint(
            "original_id",
            "original_chat_id",
            name="unique_thread",
        ),
    )

    def __hash__(self):
        return hash((self.original_chat_id, self.original_id))

    def __eq__(self, other):
        return (self.original_chat_id, self.original_id) == (
            other.chat_id,
            other.original_id,
        )


@dataclass
class Destination:
    chat: TelegramChat
    thread: TelegramThread | None

    @property
    def url(self) -> str | None:
        if chart_url := self.chat.url:
            if self.thread:
                return f"{chart_url}/{self.thread.original_id}"
            else:
                return chart_url
        return None

    def get_thread_id(self) -> int | None:
        return self.thread.id if self.thread else None

    def get_thread_original_id(self) -> int | None:
        return self.thread.original_id if self.thread else None

    def __hash__(self):
        return hash((self.chat, self.thread))

    def __eq__(self, other):
        return (self.chat, self.thread) == (other.chat, other.thread)


class Forwarding(Base):
    __tablename__ = "Forwarding"

    id: Mapped[int] = mapped_column(
        init=False,
        primary_key=True,
        autoincrement=True,
    )
    youtube_channel_id: Mapped[int] = mapped_column(
        ForeignKey(
            YouTubeChannel.id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    telegram_chat_id: Mapped[int] = mapped_column(
        ForeignKey(
            TelegramChat.original_id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    telegram_thread_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            TelegramThread.id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "youtube_channel_id",
            "telegram_chat_id",
            "telegram_thread_id",
            name="unique_forwarding",
        ),
    )

    def __eq__(self, other):
        return self.id == other.channel_id


class YouTubeVideo(Base):
    __tablename__ = "YouTubeVideos"

    id: Mapped[int] = mapped_column(
        init=False,
        primary_key=True,
        autoincrement=True,
    )
    original_id: Mapped[str] = mapped_column(unique=True)
    scan_time: Mapped[datetime] = mapped_column(DateTime)
    channel_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            YouTubeChannel.id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        default=None,
    )
    title: Mapped[str | None] = mapped_column(default=None)
    style: Mapped[str | None] = mapped_column(default=None)
    time_ago: Mapped[str | None] = mapped_column(default=None)
    creation_time: Mapped[datetime | None] = mapped_column(
        DateTime, default=None
    )
    live_24_7: Mapped[bool] = mapped_column(Boolean, default=False)
    url = property(lambda self: YT_VIDEO_URL_FMT.format(id=self.original_id))

    def __hash__(self):
        return hash(self.original_id)

    def __eq__(self, other):
        return self.original_id == other.original_id

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}


class Category(Base):
    __tablename__ = "Categories"

    id: Mapped[int] = mapped_column(
        init=False,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(unique=True)
    order: Mapped[int] = mapped_column(autoincrement=True)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.channel_id


class YTChannelCategory(Base):
    __tablename__ = "YTChannelCategories"

    id: Mapped[int] = mapped_column(
        init=False,
        primary_key=True,
        autoincrement=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            Category.id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey(
            YouTubeChannel.id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "channel_id",
            name="unique_yt_tag",
        ),
    )

    def __hash__(self):
        return hash((self.category_id, self.channel_id))

    def __eq__(self, other):
        return (self.category_id, self.channel_id) == (
            other.category_id,
            other.channel_id,
        )


class ForwardedVideo(Base):
    __tablename__ = "ForwardedVideos"

    id: Mapped[int] = mapped_column(
        init=False,
        primary_key=True,
        autoincrement=True,
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey(
            YouTubeVideo.id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    chat_original_id: Mapped[int] = mapped_column(
        ForeignKey(
            TelegramChat.original_id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    thread_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            TelegramThread.id,
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )
    __table_args__ = (
        UniqueConstraint(
            "video_id",
            "chat_original_id",
            "thread_id",
            name="unique_forwarded_video",
        ),
    )
