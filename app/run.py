import asyncio
import itertools
import pickle
import random
import subprocess
import sys
from datetime import datetime, timedelta
from logging import getLogger
from typing import Sequence

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import or_f
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from redis.asyncio import from_url
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

from .bot_ui.bot_types import BotContext, Storage
from .bot_ui.filers import ChatAdminFilter, BotAdminFilter, PrivateChatFilter
from .bot_ui.handlers import chat_admins, bot_admins
from .database.models import YouTubeChannel, YouTubeVideo
from .database.utils import (
    get_forwarding_data,
    get_last_video_ids,
    get_video_by_original_id
)
from .format_utils import (
    fmt_scan_data,
    fmt_groups,
    fmt_channel
)
from .message_utils import (
    get_tg_to_yt_videos,
    make_message_groups
)
from .send_worker import send_worker
from .settings import (
    Settings,
    LAST_DAYS_IN_DB,
    LAST_DAYS_ON_PAGE,
    MY_COMMANDS
)
from .youtube_utils import (
    get_channel_data,
    ScanData,
    YouTubeChannelData, get_video_tags
)

logger = getLogger(__name__)


async def upgrade_database(attempts=6, delay=10) -> None:
    for i in range(attempts):
        cmd = [sys.executable, '-m', 'alembic', 'upgrade', 'head']
        r = subprocess.run(cmd, capture_output=False)
        if r.returncode == 0:
            return

        logger.warning('Database is not ready!')
        await asyncio.sleep(delay)
    raise RuntimeError('Can`t upgrade database!')


async def on_startup(bot: Bot):
    logger.info("Bot started.")
    await bot.set_my_commands(MY_COMMANDS)


async def run(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    # if settings.check_migrations:
    #    logger.info('Upgrade database ...')
    #    await upgrade_database(attempts=1)

    logger.info('Create bot instance ...')
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    await bot.delete_webhook(drop_pending_updates=True)

    bot_admin_filter = BotAdminFilter(settings.bot_admin_ids)
    bot_admins.router.callback_query.filter(bot_admin_filter)
    bot_admins.router.message.filter(bot_admin_filter)

    chat_admin_filter = or_f(
        PrivateChatFilter(),  # F.chat.type == 'private' ?
        bot_admin_filter,
        ChatAdminFilter(),
    )
    chat_admins.router.message.filter(chat_admin_filter)
    chat_admins.router.callback_query.filter(chat_admin_filter)

    dp.include_routers(chat_admins.router, bot_admins.router)

    context = BotContext(settings, Storage(), session_maker)
    logger.info('Create scheduler ...')
    scheduler = AsyncIOScheduler(timezone=settings.tz)
    trigger = CronTrigger.from_crontab(
        settings.cron_schedule,
        timezone=settings.tz
    )
    scheduler.add_job(
        update,
        args=(session_maker, settings),
        trigger=trigger
    )
    scheduler.start()

    logger.info("Run tasks ...")
    dp.startup.register(on_startup)
    tasks = [
        dp.start_polling(bot, context=context),
        send_worker(settings, bot),
    ]
    await asyncio.gather(*tasks)


async def update(session_maker, settings: Settings) -> None:
    logger.info('Updating ...')

    async with session_maker() as session:
        f_data = await get_forwarding_data(session)
        tg_to_yt_channels, tg_yt_to_forwarding = f_data

        youtube_channels = list(
            set(itertools.chain.from_iterable(tg_to_yt_channels.values()))
        )
        if not settings.mode != 'dev':
            random.shuffle(youtube_channels)

        logger.info('Scan youtube channels ...')
        logger.info(f'Channel count {len(youtube_channels)}')

        scan_data = await scan_youtube_channels(youtube_channels,
                                                settings.request_delay)

        logger.info('Search new videos ...')
        new_data = await filter_data_by_time(scan_data)
        new_data = await filter_data_by_id(new_data, session)
        new_videos: frozenset[YouTubeVideo] = frozenset(
            itertools.chain.from_iterable(list(new_data.values()))
        )

        tags = {}
        if settings.parse_tags:
            logger.info(f'Parse tags of videos ...')
            for video in new_videos:
                tags[video.original_id] = await get_video_tags(video.url)
                await asyncio.sleep(settings.request_delay)

        logger.info(f'New videos: {len(new_videos)}')
        if new_videos:
            logger.info(fmt_scan_data(new_data))

            logger.info('Make message groups ...')
            tg_to_yt_videos = get_tg_to_yt_videos(
                new_data,
                tg_to_yt_channels
            )
            groups = make_message_groups(
                tg_to_yt_videos, youtube_channels, tags
            )
            logger.info('Messages:\n' + fmt_groups(groups, ' ' * 4))

            dumps = [pickle.dumps(group) for group in groups]
            async with from_url(settings.redis_url) as redis_client:
                await redis_client.rpush(settings.redis_queue, *dumps)

            logger.info('Save new videos to database ...')
            try:
                session.add_all(new_videos)
                await session.commit()
            except Exception as e:
                logger.exception(e)
        logger.info('Updating finished.')


async def scan_youtube_channels(channels: Sequence[YouTubeChannel],
                                request_delay: float) -> ScanData:
    result = {}
    for i, channel in enumerate(channels, start=1):
        logger.debug(f"{i}/{len(channels)} " + fmt_channel(channel))
        try:
            result[channel] = await get_channel_data(channel)
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
            logger.error(f'Scan error {channel.url}\n{type(e)}')
        except Exception as e:
            logger.exception(e)
        await asyncio.sleep(request_delay)
    logger.debug('Scan done!')
    return result


def filter_videos_by_time(vs: list[YouTubeVideo],
                          last_time: datetime) -> list[YouTubeVideo]:
    return list(filter(lambda v: v.creation_time >= last_time, vs))


async def filter_videos_by_id(videos: list[YouTubeVideo],
                              last_ids: frozenset[str]) -> list[YouTubeVideo]:
    result = []
    for video in videos:
        if video.original_id not in last_ids:
            result.append(video)
    return result


async def filter_streams_by_id(streams: list[YouTubeVideo],
                               last_ids: frozenset[str],
                               session: AsyncSession) -> list[YouTubeVideo]:
    result = []
    for stream in streams:
        if stream.original_id not in last_ids:
            if exist_stream := await get_video_by_original_id(
                    stream.original_id,
                    session
            ):
                if 'LIVE' in (stream.style, exist_stream.style):
                    exist_stream.style = 'LIVE'
                    exist_stream.live_24_7 = True
                    await session.merge(exist_stream)
            else:
                result.append(stream)
    return result


async def filter_data_by_time(scan_data: ScanData) -> ScanData:
    new_data: ScanData = {}
    last_time = datetime.today() - timedelta(days=LAST_DAYS_ON_PAGE)
    for channel, data in scan_data.items():
        new_data[channel] = YouTubeChannelData(
            videos=filter_videos_by_time(data.videos, last_time),
            streams=filter_videos_by_time(data.streams, last_time)
        )
    return new_data


async def filter_data_by_id(scan_data: ScanData,
                            session: AsyncSession) -> ScanData:
    new_data: ScanData = {}
    for channel, data in scan_data.items():
        assert channel.id is not None
        if data.videos or data.streams:
            last_video_ids = await get_last_video_ids(
                channel.id,  # noqa
                LAST_DAYS_IN_DB,
                session
            )
            videos = await filter_videos_by_id(
                data.videos,
                last_video_ids
            )
            streams = await filter_streams_by_id(
                data.streams,
                last_video_ids,
                session
            )
            new_data[channel] = YouTubeChannelData(
                videos=videos,
                streams=streams
            )
    return new_data
