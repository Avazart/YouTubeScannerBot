from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, TypeAlias

import sqlalchemy
from sqlalchemy.engine import ChunkedIteratorResult, Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import Select
from sqlalchemy.sql.expression import select, exists, delete, distinct, update, desc
from sqlalchemy.sql.functions import count

from bot_ui.bot_types import Status
from database.models import (
    TelegramChat,
    Forwarding,
    YouTubeVideo,
    YouTubeChannel,
    Tag,
    YouTubeChannelTag,
    TelegramThread,
    Destination
)

TgToYouTubeChannels: TypeAlias = dict[Destination, list[YouTubeChannel]]
TgYtToForwarding: TypeAlias = dict[(Destination, YouTubeChannel), Forwarding]
ForwardingData: TypeAlias = tuple[TgToYouTubeChannels, TgYtToForwarding]


# Forwarding

async def get_forwarding_data(session: AsyncSession) -> ForwardingData:
    q: Select = select(TelegramChat, TelegramThread, YouTubeChannel, Forwarding) \
        .join(YouTubeChannel) \
        .join(TelegramChat) \
        .join(TelegramThread,
              TelegramThread.id == Forwarding.telegram_thread_id,
              isouter=True) \
        .where(TelegramChat.status == int(Status.ON)) \
        .order_by(Forwarding.youtube_channel_id)
    result: ChunkedIteratorResult = await session.execute(q)
    tg_to_youtube_channels = {}
    tg_yt_to_forwarding = {}
    for row in result.fetchall():
        tg = Destination(chat=row[0], thread=row[1])
        channel, forwarding = row[2], row[3]
        tg_to_youtube_channels.setdefault(tg, []).append(channel)
        tg_yt_to_forwarding[(tg, channel)] = forwarding
    return tg_to_youtube_channels, tg_yt_to_forwarding


async def add_forwarding(youtube_channel_id: int,
                         telegram_chat_id: int,
                         telegram_thread_id: Optional[int],
                         session: AsyncSession):
    f = Forwarding(youtube_channel_id=youtube_channel_id,
                   telegram_chat_id=telegram_chat_id,
                   telegram_thread_id=telegram_thread_id)
    await session.merge(f)


async def delete_forwarding(youtube_channel_id: int,
                            telegram_chat_id: int,
                            telegram_thread_id: Optional[int],
                            session: AsyncSession):
    q = delete(Forwarding).where((Forwarding.youtube_channel_id == youtube_channel_id) &
                                 (Forwarding.telegram_chat_id == telegram_chat_id) &
                                 (Forwarding.telegram_thread_id == telegram_thread_id))

    await session.execute(q)


# YouTubeChannel

async def get_yt_channel_title_by_id(channel_id: str,
                                     session: AsyncSession) -> Optional[str]:
    q: Select = select(YouTubeChannel.title).where(YouTubeChannel.id == channel_id)
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0]
    return None


async def get_yt_channel_by_id(channel_id: str, session: AsyncSession) -> Optional[YouTubeChannel]:
    q = select(YouTubeChannel).where(YouTubeChannel.id == channel_id)
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0]
    return None


async def get_yt_channel_id_by_original_id(original_id: str, session: AsyncSession) -> Optional[int]:
    q = select(YouTubeChannel).where(YouTubeChannel.original_id == original_id)
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0].id
    return None


async def get_yt_channels(tg_chat_id: int,
                          tg_thread_id: Optional[int],
                          tag_ids: set[int],
                          offset: Optional[int],
                          limit: Optional[int],
                          session: AsyncSession):
    q = select(YouTubeChannel,
               exists(select(Forwarding)
                      .join(TelegramThread,
                            TelegramThread.id == Forwarding.telegram_thread_id,
                            isouter=True)
                      .where((Forwarding.telegram_chat_id == tg_chat_id) &
                             (TelegramThread.original_id == tg_thread_id) &
                             (Forwarding.youtube_channel_id == YouTubeChannel.id))
                      ).label("enabled")
               )

    if tag_ids:
        q = q.join(YouTubeChannelTag, YouTubeChannelTag.tag_id.in_(tag_ids)) \
            .where(YouTubeChannel.id == YouTubeChannelTag.channel_id) \
            .group_by(YouTubeChannelTag.channel_id) \
            .having(count(distinct(YouTubeChannelTag.tag_id)) == len(tag_ids))
    else:
        q = q.order_by(desc('enabled'))

    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)

    result = await session.execute(q)
    rows: list[Row] = result.fetchall()
    return rows


#  YouTubeVideo

async def get_last_video_ids(channel_id: int,
                             last_days: int,
                             session: AsyncSession) -> frozenset[str]:
    last_time = datetime.today() - timedelta(days=last_days)
    q = select(YouTubeVideo) \
        .where((YouTubeVideo.channel_id == channel_id) &
               ((YouTubeVideo.creation_time >= last_time) | (YouTubeVideo.live_24_7 == True))
               ) \
        .order_by(YouTubeVideo.creation_time.desc())
    result = await session.execute(q)
    rows: list[Row] = result.fetchall()
    return frozenset((row[0].original_id for row in rows))


async def get_video_by_original_id(original_id: str,
                                   session: AsyncSession) -> Optional[YouTubeVideo]:
    q = select(YouTubeVideo).where(YouTubeVideo.original_id == original_id)
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0]
    return None


# Telegram

async def tg_by_user_name(user_name: str,
                          session: AsyncSession) -> Optional[TelegramChat]:
    q: Select = select(TelegramChat).where(TelegramChat.user_name == user_name)
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0]
    return None


async def get_destinations(original_chat_id: int,
                           original_thread_id: Optional[int],
                           session: AsyncSession) -> Optional[Destination]:
    q = select(TelegramChat, TelegramThread) \
        .join(TelegramThread,
              TelegramChat.original_id == TelegramThread.original_chat_id,
              isouter=True) \
        .where((TelegramChat.original_id == original_chat_id) &
               (TelegramThread.original_id == original_thread_id))
    result = await session.execute(q)
    if row := result.fetchone():
        return Destination(chat=row[0], thread=row[1])
    return None


async def set_telegram_chat_status(chat_id: int,
                                   status: Status,
                                   session: AsyncSession):
    q = update(TelegramChat) \
        .values({"status": int(status.next())}) \
        .where(TelegramChat.original_id == chat_id)
    await session.execute(q)


# TAG

async def get_tag_id_by_name(tag_name: str,
                             session: AsyncSession) -> Optional[int]:
    q = select(Tag).where(Tag.name == tag_name)
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0].id
    return None


async def delete_channel_by_original_id(original_id: str, session: AsyncSession):
    q = delete(YouTubeChannel).where(YouTubeChannel.original_id == original_id)
    await session.execute(q)


async def delete_tag_by_name(tag_name: str,
                             session: AsyncSession):
    q = delete(Tag).where(Tag.name == tag_name)
    await session.execute(q)


async def get_tags(offset: Optional[int],
                   limit: Optional[int],
                   session: AsyncSession) -> list[Tag]:
    q = select(Tag).order_by(Tag.order)
    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    result = await session.execute(q)
    rows: list[Row] = result.fetchall()
    return [row[0] for row in rows]


async def add_yt_channel_tag(tag_id: int, channel_id: str, session: AsyncSession):
    yt_tag = YouTubeChannelTag(tag_id=tag_id, channel_id=channel_id)
    await session.merge(yt_tag)


async def delete_yt_channel_tag(tag_id: int, channel_id: str, session: AsyncSession):
    q = delete(YouTubeChannelTag).where((YouTubeChannelTag.tag_id == tag_id) &
                                        (YouTubeChannelTag.channel_id == channel_id))
    await session.execute(q)


async def get_yt_channel_tags(yt_channel_id: str,
                              offset: Optional[int],
                              limit: Optional[int],
                              session: AsyncSession) -> list[(YouTubeChannel, bool)]:
    q = select(Tag,
               exists(select(YouTubeChannelTag).where(
                   (YouTubeChannelTag.channel_id == yt_channel_id) &
                   (YouTubeChannelTag.tag_id == Tag.id)
               ))) \
        .order_by(Tag.order)
    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    result = await session.execute(q)
    rows: list[Row] = result.fetchall()
    return rows


async def get_tgs(offset: Optional[int],
                  limit: Optional[int],
                  session: AsyncSession) -> list[Destination]:
    q = select(TelegramChat, TelegramThread) \
        .join(TelegramThread,
              TelegramChat.original_id == TelegramThread.original_chat_id,
              isouter=True)
    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    result = await session.execute(q)
    rows: list[Row] = result.fetchall()
    return [Destination(chat=row[0], thread=row[1]) for row in rows]


async def create_views(file_path: Path, connection):
    text = file_path.read_text('utf-8')
    for statement in text.split(';'):
        await connection.execute(sqlalchemy.text(statement))
