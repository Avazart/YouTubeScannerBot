from datetime import datetime, timedelta
from pathlib import Path
from typing import TypeAlias, Optional

import sqlalchemy
from sqlalchemy.engine import ChunkedIteratorResult, Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import Select

from database_models import TelegramObject, Forwarding, YouTubeVideo, YouTubeChannel

ForwardingData: TypeAlias = dict[TelegramObject, list[YouTubeChannel]]


async def get_forwarding_data(session: AsyncSession, enabled_only=True) -> ForwardingData:
    q: Select = select(TelegramObject, YouTubeChannel).select_from(Forwarding) \
        .join_from(YouTubeChannel, TelegramObject,
                   (Forwarding.youtube_channel_id == YouTubeChannel.id) &
                   (Forwarding.telegram_id == TelegramObject.id) &
                   ((not enabled_only) or (Forwarding.enabled >= 1))) \
        .order_by(Forwarding.youtube_channel_id)
    result: ChunkedIteratorResult = await session.execute(q)  #
    data = {}
    for row in result.fetchall():
        data.setdefault(row[0], []).append(row[1])
    return data


async def get_last_video_ids(channel_id: str,
                             count: int,
                             last_days: int,
                             session: AsyncSession) -> list[str]:
    last_time = datetime.today() - timedelta(days=last_days)
    q = select(YouTubeVideo) \
        .where((YouTubeVideo.channel_id == channel_id) &
               (YouTubeVideo.creation_time >= last_time)) \
        .order_by(YouTubeVideo.creation_time.desc()) \
        .limit(count)
    result = await session.execute(q)
    rows: list[Row] = result.fetchall()
    return [row[0].id for row in rows]


async def telegram_object_by_user_name(user_name: str,
                                       session: AsyncSession) -> Optional[TelegramObject]:
    q: Select = select(TelegramObject).where(TelegramObject.user_name == user_name)
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0]
    return None


async def get_channel_title_by_id(channel_id: str,
                                  session: AsyncSession) -> Optional[str]:
    q: Select = select(YouTubeChannel.title).where(YouTubeChannel.id == channel_id)
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0]
    return None


async def get_forwarding(yt_channel_id: str,
                         tg_id: int,
                         session: AsyncSession) -> Optional[Forwarding]:
    q: Select = select(Forwarding).where((Forwarding.youtube_channel_id == yt_channel_id) &
                                         (Forwarding.telegram_id == tg_id))
    result: ChunkedIteratorResult = await session.execute(q)
    if rows := result.fetchone():
        return rows[0]
    return None


async def add_forwarding(yt_channel: YouTubeChannel,
                         tg: TelegramObject,
                         enabled: bool,
                         session: AsyncSession) -> None:
    await session.merge(yt_channel)
    await session.merge(tg)
    existing_forwarding = await get_forwarding(yt_channel.id, tg.id, session)
    forwarding = Forwarding(n=existing_forwarding.n if existing_forwarding else None,
                            youtube_channel_id=yt_channel.id,
                            telegram_id=tg.id,
                            enabled=enabled)
    await session.merge(forwarding)


async def create_views(file_path: Path, connection):
    text = file_path.read_text('utf-8')
    for statement in text.split(';'):
        await connection.execute(sqlalchemy.text(statement))
