import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta
from logging import getLogger

import aiohttp
from aiogram import Bot
from aiogram.enums import ChatType, ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from .bot.keyboards import video_links_keyboard
from .constants import LAST_DAYS_IN_DB, LAST_DAYS_ON_PAGE
from .database.models import Destination, YouTubeChannel, YouTubeVideo
from .database.services import (
    ForwardedVideoService,
    ForwardingService,
    YTChannelService,
    YTVideoService,
)
from .format_utils import fmt_channel, make_message_text, make_video_line
from .send_worker import try_send_message
from .settings import Settings
from .youtube_parser import search
from .youtube_utils import get_channel_data

logger = getLogger(__name__)


async def scan(session_maker, settings: Settings) -> None:
    async with session_maker() as session:
        channel_service = YTChannelService(session)
        channels = await channel_service.get_all_active()
        logger.info("ChannelMenuData count %d", len(channels))

        logger.info("Scan youtube channels ...")
        videos = await scan_youtube_channels(channels, settings.request_delay)
        recent_videos = get_recent_videos(videos, LAST_DAYS_ON_PAGE)

        logger.info("Recent videos: %d", len(recent_videos))
        # logger.debug(pformat(recent_videos))
        if recent_videos:
            video_service = YTVideoService(session)
            await video_service.insert(recent_videos)
            await session.commit()
        logger.info("Scanning complete.")


async def notify(session_maker, settings: Settings, bot: Bot) -> None:
    logger.info("Notification ...")

    async with session_maker() as session:
        forwarding_service = ForwardingService(session)
        forwarded_video_service = ForwardedVideoService(session)
        dest_with_channels, _ = await forwarding_service.get_data()
        channel_titles = {}
        for channels in dest_with_channels.values():
            for channel in channels:
                channel_titles[channel.id] = channel.title

        for dest, channels in dest_with_channels.items():
            limit = 2 if dest.chat.type == ChatType.CHANNEL else 5

            videos = await forwarded_video_service.get_not_forwarded(
                dest, channels, last_days=LAST_DAYS_IN_DB, limit=limit
            )
            logger.info(
                "%s%s videos: %d",
                dest.chat.title or dest.chat.first_name,
                ("/" + dest.thread.title)
                if dest.thread and dest.thread.title
                else "",
                len(videos),
            )

            if videos:
                await send_videos(
                    dest, videos, channel_titles, session, bot, settings
                )
    logger.info("Notification completed.")


async def send_videos(
    dest: Destination,
    videos: list[YouTubeVideo],
    channel_titles: dict,
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
):
    dispatched_videos = []
    logger.debug(dest)
    if dest.chat.type.lower() == ChatType.CHANNEL:
        for video in videos:
            if await try_send_message(
                bot,
                dest.chat.original_id,
                make_video_line(video, channel_titles),
                settings,
                message_thread_id=dest.get_thread_original_id(),
                parse_mode=ParseMode.HTML,
            ):
                dispatched_videos.append(video)
            await asyncio.sleep(settings.message_delay)
    else:  # GROUPS, PRIVATE
        text = make_message_text(videos, channel_titles)
        if await try_send_message(
            bot,
            dest.chat.original_id,
            text,
            settings,
            message_thread_id=dest.get_thread_original_id(),
            parse_mode=ParseMode.HTML,
            reply_markup=video_links_keyboard(1, len(videos)),
        ):
            dispatched_videos = videos

    if dispatched_videos:
        forwarded_video_service = ForwardedVideoService(session)
        await forwarded_video_service.add_forwarded(dest, dispatched_videos)
        await session.commit()
    await asyncio.sleep(settings.message_delay)


async def scan_youtube_channels(
    channels: Sequence[YouTubeChannel],
    request_delay: float,
) -> list[YouTubeVideo]:
    result: list[YouTubeVideo] = []
    for i, channel in enumerate(channels, start=1):
        logger.debug("%d/%d %s", i, len(channels), fmt_channel(channel))
        try:
            result.extend(await get_channel_data(channel))
        except (TimeoutError, aiohttp.ClientConnectorError) as e:
            logger.error(
                "Scan error %s\n%s\n%s", channel.title, channel.url, type(e)
            )
        except search.SearchError:
            logger.exception(
                "Search error %s\n%s", channel.title, channel.title
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(e)
        await asyncio.sleep(request_delay)
    return result


def get_recent_videos(vs: list[YouTubeVideo], days: int) -> list[YouTubeVideo]:
    last_time = datetime.today() - timedelta(days=days)
    return list(filter(lambda v: v.creation_time >= last_time, vs))
