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
from aiogram import Dispatcher, Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from redis.asyncio import from_url
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

from .bot_ui.bot_types import BotContext, Storage
from .bot_ui.callbacks import register_callback_queries
from .bot_ui.commands import register_commands
from .bot_ui.filers import ChatAdminFilter, BotAdminFilter
from .database.models import YouTubeChannel, YouTubeVideo
from .database.utils import (
    get_forwarding_data,
    get_last_video_ids,
    get_video_by_original_id)
from .format_utils import fmt_scan_data, fmt_groups, fmt_channel
from .message_utils import (
    get_tg_to_yt_videos,
    make_message_groups
)
from .send_worker import send_worker
from .settings import (
    Settings,
    LAST_DAYS_IN_DB,
    LAST_DAYS_ON_PAGE
)
from .youtube_utils import (
    get_channel_data,
    ScanData,
    YouTubeChannelData
)

logger = getLogger(__name__)


async def upgrade_database(attempts=6, delay=10):
    for i in range(attempts):
        cmd = [sys.executable, '-m', 'alembic', 'upgrade', 'head']
        r = subprocess.run(cmd, capture_output=False)
        if r.returncode == 0:
            return

        logger.warning('Database is not ready!')
        await asyncio.sleep(delay)
    raise RuntimeError('Can`t upgrade database!')


async def run(settings: Settings):
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    logger.info('Upgrade database ...')
    await upgrade_database(attempts=1)

    logger.info('Create bot instance ...')
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    bot_admin_filter = BotAdminFilter(settings.bot_admin_ids)
    chat_admin_filter = ChatAdminFilter(settings.bot_admin_ids)
    register_commands(dp, chat_admin_filter, bot_admin_filter)
    register_callback_queries(dp, chat_admin_filter, bot_admin_filter)
    context = BotContext(settings, Storage(), session_maker)

    logger.info('Create scheduler ...')
    scheduler = AsyncIOScheduler(timezone=settings.tz)
    trigger = CronTrigger.from_crontab(settings.cron_schedule,
                                       timezone=settings.tz)
    scheduler.add_job(update,
                      args=(session_maker, settings),
                      trigger=trigger)
    scheduler.start()

    tasks = [
        dp.start_polling(bot, skip_updates=True, context=context),
        send_worker(settings, bot),
    ]
    await asyncio.gather(*tasks)


async def update(session_maker, settings: Settings):
    async with session_maker() as session:
        logger.info('Updating ...')

        tg_to_yt_channels, tg_yt_to_forwarding = \
            await get_forwarding_data(session)
        youtube_channels = list(
            set(itertools.chain.from_iterable(tg_to_yt_channels.values()))
        )
        if not settings.mode != 'dev':
            random.shuffle(youtube_channels)
        logger.info(f'Channel count {len(youtube_channels)}')

        logger.info('Scan youtube channels ...')
        scan_data = await scan_youtube_channels(youtube_channels,
                                                settings.request_delay)

        logger.info('Search new videos ...')
        new_data = await get_new_data(scan_data, session)
        new_videos = frozenset(
            itertools.chain.from_iterable(list(new_data.values()))
        )
        logger.info(f'New videos: {len(new_videos)}')
        if new_videos:
            logger.info(fmt_scan_data(new_data))
            logger.info('Make message groups ...')
            tg_to_yt_videos = get_tg_to_yt_videos(new_data, tg_to_yt_channels)

            groups = make_message_groups(tg_to_yt_videos, youtube_channels)
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
        logger.info('Updating finished')


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


async def get_new_data(scan_data: ScanData, session: AsyncSession) -> ScanData:
    new_data: ScanData = {}
    last_time = datetime.today() - timedelta(days=LAST_DAYS_ON_PAGE)

    def filter_by_time(vs: list[YouTubeVideo]) -> list[YouTubeVideo]:
        return list(filter(lambda v: v.creation_time >= last_time, vs))

    for channel, data in scan_data.items():
        assert channel.id is not None

        new_videos = []
        new_streams = []

        if data.videos or data.streams:
            last_video_ids = await get_last_video_ids(channel.id,
                                                      LAST_DAYS_IN_DB,
                                                      session)

            # /videos
            videos = filter_by_time(data.videos)
            for video in videos:
                if video.original_id not in last_video_ids:
                    new_videos.append(video)

            # /streams
            streams = filter_by_time(data.streams)
            for stream in streams:
                if stream.original_id not in last_video_ids:
                    if exist_stream := await get_video_by_original_id(
                            stream.original_id,
                            session
                    ):
                        if 'LIVE' in (stream.style, exist_stream.style):
                            exist_stream.style = 'LIVE'
                            exist_stream.live_24_7 = True
                            await session.merge(exist_stream)
                        else:
                            logger.warning(f"Conflict {stream=} "
                                           f"and {exist_stream=}")
                    else:
                        new_streams.append(stream)

            new_data[channel] = YouTubeChannelData(
                videos=new_videos,
                streams=new_streams
            )
    return new_data
