import logging
from datetime import datetime, timedelta
from typing import TypeAlias

from sqlalchemy import distinct
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import (
    delete,
    desc,
    exists,
    select,
    update,
)
from sqlalchemy.sql.functions import count

from ..bot_ui.bot_types import Status
from .models import (
    Category,
    Destination,
    ForwardedVideo,
    Forwarding,
    TelegramChat,
    TelegramThread,
    YouTubeChannel,
    YouTubeVideo,
    YTChannelCategory,
)

TgToYouTubeChannels: TypeAlias = dict[Destination, list[YouTubeChannel]]
TgYtToForwarding: TypeAlias = dict[
    tuple[Destination, YouTubeChannel], Forwarding
]
ForwardingData: TypeAlias = tuple[TgToYouTubeChannels, TgYtToForwarding]

logger = logging.getLogger(__name__)


async def get_active_yt_channels(
    session: AsyncSession,
) -> list[YouTubeChannel]:
    q = (
        select(YouTubeChannel)
        .join(Forwarding, YouTubeChannel.id == Forwarding.youtube_channel_id)
        .join(
            TelegramChat,
            TelegramChat.original_id == Forwarding.telegram_chat_id,
        )
        .where(TelegramChat.status == int(Status.ON))
        .distinct()
        .order_by(YouTubeChannel.id)
    )
    result = await session.execute(q)
    return result.scalars().all()  # type: ignore


async def get_active_destinations(session: AsyncSession) -> list[Destination]:
    q = (
        select(TelegramChat, TelegramThread)
        .join(
            Forwarding, TelegramChat.original_id == Forwarding.telegram_chat_id
        )
        .outerjoin(
            TelegramThread, TelegramThread.id == Forwarding.telegram_thread_id
        )
        .where(TelegramChat.status == int(Status.ON))
    )
    result = await session.execute(q)
    return [Destination(chat=row[0], thread=row[1]) for row in result.all()]


async def insert_videos(
    session: AsyncSession,
    videos: list[YouTubeVideo],
) -> None:
    q = insert(YouTubeVideo).values([v.as_dict() for v in videos])
    q = q.on_conflict_do_nothing(index_elements=["original_id"])
    await session.execute(q)
    await session.commit()


async def add_forwarded_videos(
    session: AsyncSession,
    dest: Destination,
    videos: list[YouTubeVideo],
) -> None:
    f_videos = [
        ForwardedVideo(
            video_id=video.id,
            chat_original_id=dest.chat.original_id,
            thread_id=dest.get_thread_id(),
        )
        for video in videos
    ]
    session.add_all(f_videos)
    await session.commit()


async def get_not_forwarded_videos(
    session: AsyncSession,
    dest: Destination,
    channels: list[YouTubeChannel],
    last_days: int | None = None,
    limit: int = 5,
) -> list[YouTubeVideo]:
    channel_ids = (ch.id for ch in channels)

    forwarded_subquery = select(ForwardedVideo.video_id).where(
        (ForwardedVideo.chat_original_id == dest.chat.original_id)
        & (ForwardedVideo.thread_id == dest.get_thread_id())
    )

    q = select(YouTubeVideo).filter(
        YouTubeVideo.channel_id.in_(channel_ids)
        & (~YouTubeVideo.id.in_(forwarded_subquery))
    )
    if last_days:
        last_time = datetime.today() - timedelta(days=last_days)
        q = q.where(YouTubeVideo.creation_time >= last_time)

    q = q.order_by(YouTubeVideo.creation_time.desc()).limit(limit)

    result = await session.execute(q)
    return result.scalars().all()  # type: ignore


async def get_forwarding_data(session: AsyncSession) -> ForwardingData:
    q = (
        select(TelegramChat, TelegramThread, YouTubeChannel, Forwarding)
        .join(YouTubeChannel)
        .join(TelegramChat)
        .join(
            TelegramThread,
            TelegramThread.id == Forwarding.telegram_thread_id,
            isouter=True,
        )
        .where(TelegramChat.status == int(Status.ON))
        .order_by(Forwarding.youtube_channel_id)
    )
    result = await session.execute(q)
    tg_to_youtube_channels: TgToYouTubeChannels = {}
    tg_yt_to_forwarding: TgYtToForwarding = {}
    for row in result.fetchall():
        tg = Destination(chat=row[0], thread=row[1])
        channel, forwarding = row[2], row[3]
        tg_to_youtube_channels.setdefault(tg, []).append(channel)
        tg_yt_to_forwarding[(tg, channel)] = forwarding
    return tg_to_youtube_channels, tg_yt_to_forwarding


async def add_forwarding(
    youtube_channel_id: int,
    telegram_chat_id: int,
    telegram_thread_id: int | None,
    session: AsyncSession,
) -> None:
    f = Forwarding(
        youtube_channel_id=youtube_channel_id,
        telegram_chat_id=telegram_chat_id,
        telegram_thread_id=telegram_thread_id,
    )
    await session.merge(f)


async def delete_forwarding(
    youtube_channel_id: int,
    telegram_chat_id: int,
    telegram_thread_id: int | None,
    session: AsyncSession,
) -> None:
    q = delete(Forwarding).where(
        (Forwarding.youtube_channel_id == youtube_channel_id)
        & (Forwarding.telegram_chat_id == telegram_chat_id)
        & (Forwarding.telegram_thread_id == telegram_thread_id)
    )
    await session.execute(q)


# YouTubeChannel


async def get_yt_channel_title_by_id(
    channel_id: str,
    session: AsyncSession,
) -> str | None:
    q = select(YouTubeChannel.title).where(YouTubeChannel.id == channel_id)
    return await session.scalar(q)


async def get_yt_channel_by_id(
    channel_id: int,
    session: AsyncSession,
) -> YouTubeChannel | None:
    q = select(YouTubeChannel).where(YouTubeChannel.id == channel_id)
    return await session.scalar(q)


async def get_yt_channel_id(
    original_id: str,
    session: AsyncSession,
) -> int | None:
    q = select(YouTubeChannel.id).where(
        YouTubeChannel.original_id == original_id
    )
    return await session.scalar(q)


async def get_yt_channels(
    tg_chat_id: int,
    tg_thread_id: int | None,
    category_ids: set[int],
    offset: int | None,
    limit: int | None,
    session: AsyncSession,
) -> list[tuple[YouTubeChannel, bool]]:
    q = select(
        YouTubeChannel,
        exists(
            select(Forwarding)
            .join(
                TelegramThread,
                TelegramThread.id == Forwarding.telegram_thread_id,
                isouter=True,
            )
            .where(
                (Forwarding.telegram_chat_id == tg_chat_id)
                & (TelegramThread.original_id == tg_thread_id)
                & (Forwarding.youtube_channel_id == YouTubeChannel.id)
            )
        ).label("enabled"),
    )

    if category_ids:
        q = (
            q.join(
                YTChannelCategory,
                YTChannelCategory.category_id.in_(category_ids),
            )
            .where(YouTubeChannel.id == YTChannelCategory.channel_id)
            .group_by(YouTubeChannel.id, YTChannelCategory.channel_id)
            .having(
                count(distinct(YTChannelCategory.category_id))
                == len(category_ids)
            )
        )
    else:
        q = q.order_by(desc("enabled"))

    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)

    result = await session.execute(q)
    rows = result.fetchall()
    return [(row[0], row[1]) for row in rows]


#  YouTubeVideo


async def get_video_by_original_id(
    original_id: str,
    session: AsyncSession,
) -> YouTubeVideo | None:
    q = select(YouTubeVideo).where(YouTubeVideo.original_id == original_id)
    return await session.scalar(q)


# Telegram


async def tg_by_user_name(
    user_name: str,
    session: AsyncSession,
) -> TelegramChat | None:
    q = select(TelegramChat).where(TelegramChat.user_name == user_name)
    return await session.scalar(q)


async def get_destinations(
    original_chat_id: int,
    original_thread_id: int | None,
    session: AsyncSession,
) -> Destination | None:
    q = (
        select(TelegramChat, TelegramThread)
        .join(
            TelegramThread,
            TelegramChat.original_id == TelegramThread.original_chat_id,
            isouter=True,
        )
        .where(
            (TelegramChat.original_id == original_chat_id)
            & (TelegramThread.original_id == original_thread_id)
        )
    )
    result = await session.execute(q)
    if row := result.fetchone():
        return Destination(chat=row[0], thread=row[1])
    return None


async def set_telegram_chat_status(
    chat_id: int,
    status: Status,
    session: AsyncSession,
) -> None:
    q = (
        update(TelegramChat)
        .values({"status": int(status.next())})
        .where(TelegramChat.original_id == chat_id)
    )
    await session.execute(q)


# CATEGORY


async def get_category_id_by_name(
    category_name: str,
    session: AsyncSession,
) -> int | None:
    q = select(Category.id).where(Category.name == category_name)
    return await session.scalar(q)


async def delete_channel_by_original_id(
    original_id: str,
    session: AsyncSession,
) -> None:
    q = delete(YouTubeChannel).where(YouTubeChannel.original_id == original_id)
    await session.execute(q)


async def delete_category_by_name(
    category_name: str,
    session: AsyncSession,
) -> None:
    q = delete(Category).where(Category.name == category_name)
    await session.execute(q)


async def get_categories(
    offset: int | None,
    limit: int | None,
    session: AsyncSession,
) -> list[Category]:
    q = select(Category).order_by(Category.order)
    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    return list((await session.scalars(q)).all())


async def add_yt_channel_category(
    category_id: int,
    channel_id: int,
    session: AsyncSession,
) -> None:
    yt_category = YTChannelCategory(
        category_id=category_id, channel_id=channel_id
    )
    await session.merge(yt_category)


async def delete_yt_channel_category(
    category_id: int,
    channel_id: int,
    session: AsyncSession,
) -> None:
    q = delete(YTChannelCategory).where(
        (YTChannelCategory.category_id == category_id)
        & (YTChannelCategory.channel_id == channel_id)
    )
    await session.execute(q)


async def get_yt_channel_categories(
    yt_channel_id: int,
    offset: int | None,
    limit: int | None,
    session: AsyncSession,
) -> list[tuple[YTChannelCategory, bool]]:
    q = select(
        Category,
        exists(
            select(YTChannelCategory).where(
                (YTChannelCategory.channel_id == yt_channel_id)
                & (YTChannelCategory.category_id == Category.id)
            )
        ),
    ).order_by(Category.order)
    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    result = await session.execute(q)
    rows = result.fetchall()
    return [(row[0], row[1]) for row in rows]


async def get_tgs(
    offset: int | None,
    limit: int | None,
    session: AsyncSession,
) -> list[Destination]:
    q = select(TelegramChat, TelegramThread).join(
        TelegramThread,
        TelegramChat.original_id == TelegramThread.original_chat_id,
        isouter=True,
    )
    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    result = await session.execute(q)
    rows = result.fetchall()
    return [Destination(chat=row[0], thread=row[1]) for row in rows]
