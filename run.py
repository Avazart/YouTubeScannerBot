import asyncio
import itertools
import pickle
import random
from datetime import datetime, timedelta
from logging import Logger
from pathlib import Path
from typing import Sequence

import aiohttp
import redis.asyncio
import tzlocal
from aiogram import Dispatcher, Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backup_utils import import_data
from bot_ui.bot_types import BotContext, Storage
from bot_ui.callbacks import register_callback_queries
from bot_ui.commands import register_commands
from bot_ui.filers import ChatAdminFilter, BotAdminFilter
from database.models import YouTubeChannel, YouTubeVideo, Base
from database.utils import (
    get_forwarding_data,
    get_last_video_ids,
    get_video_by_original_id,
    create_views)
from format_utils import fmt_scan_data, fmt_groups, fmt_channel
from message_utils import (
    get_tg_to_yt_videos,
    make_message_groups
)
from send_worker import send_worker
from settings import (
    Settings,
    LAST_DAYS_IN_DB,
    LAST_DAYS_ON_PAGE, VIEWS_SCRIPT_PATH, BACKUP_FILE_PATH
)
from youtube_utils import get_channel_data, ScanData, YouTubeChannelData


async def run(settings: Settings, logger: Logger):
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        exists_table_names = set(await connection.run_sync(
            lambda c: inspect(c).get_table_names()
        ))
        model_table_names = set(Base.metadata.tables)
        diff = model_table_names - exists_table_names
        if len(diff) == len(model_table_names):
            for table_name in diff:
                logger.debug(f'Create table "{table_name}"')
                table = Base.metadata.tables[table_name]
                await connection.run_sync(table.create)
            if BACKUP_FILE_PATH.exists():
                await import_data(Path(BACKUP_FILE_PATH), session_maker)
            if VIEWS_SCRIPT_PATH.exists():
                await create_views(VIEWS_SCRIPT_PATH, connection)

    bot = Bot(token=settings.token)
    dp = Dispatcher()

    bot_admin_filter = BotAdminFilter(settings.bot_admin_ids)
    chat_admin_filter = ChatAdminFilter(settings.bot_admin_ids)

    register_commands(dp, chat_admin_filter, bot_admin_filter)
    register_callback_queries(dp, chat_admin_filter, bot_admin_filter)

    scheduler = AsyncIOScheduler(timezone=str(tzlocal.get_localzone()))
    trigger = CronTrigger.from_crontab(settings.cron_schedule,
                                       timezone=str(tzlocal.get_localzone()))
    scheduler.add_job(update,
                      args=(session_maker, settings, logger),
                      trigger=trigger)
    scheduler.start()

    context = BotContext(logger, session_maker, settings, Storage())
    tasks = [
        dp.start_polling(bot, skip_updates=True, context=context),
        send_worker(settings, bot, logger),
    ]
    await asyncio.gather(*tasks)


async def update(session_maker,
                 settings: Settings,
                 logger: Logger):

    async with session_maker() as session:
        logger.info('Updating ...')
        tg_to_yt_channels, tg_yt_to_forwarding = await get_forwarding_data(session)
        youtube_channels = list(
            set(itertools.chain.from_iterable(tg_to_yt_channels.values()))
        )
        random.shuffle(youtube_channels)
        logger.info(f'Channel count {len(youtube_channels)}')

        logger.info('Scan youtube channels ...')
        scan_data = await scan_youtube_channels(youtube_channels,
                                                settings.request_delay,
                                                logger)

        logger.info('Search new videos ...')
        new_data = await get_new_data(scan_data, session, logger)
        new_videos = frozenset(itertools.chain.from_iterable(list(new_data.values())))

        logger.info(f'New videos: {len(new_videos)}')
        if new_videos:
            logger.info(fmt_scan_data(new_data))
            logger.info('Make message groups ...')
            tg_to_yt_videos = get_tg_to_yt_videos(new_data, tg_to_yt_channels)

            groups = make_message_groups(tg_to_yt_videos, youtube_channels)
            dumps = [pickle.dumps(group) for group in groups]

            async with redis.asyncio.from_url(settings.redis_url) as redis_client:
                await redis_client.rpush(settings.redis_queue, *dumps)

            logger.info('Messages:\n' + fmt_groups(groups, ' ' * 4))
            logger.info('Save new videos to database ...')
            try:
                session.add_all(new_videos)
                await session.commit()
            except Exception as e:
                logger.exception(e)
        logger.info('Updating finished')


async def scan_youtube_channels(channels: Sequence[YouTubeChannel],
                                request_delay: float,
                                logger: Logger) -> ScanData:
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


async def get_new_data(scan_data: ScanData,
                       session: AsyncSession,
                       logger: Logger) -> ScanData:
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
                    if exist_stream := await get_video_by_original_id(stream.original_id,
                                                                      session):
                        if 'LIVE' in (stream.style, exist_stream.style):
                            exist_stream.style = 'LIVE'
                            exist_stream.live_24_7 = True
                            await session.merge(exist_stream)
                        else:
                            logger.warning(f"Conflict {stream=} and {exist_stream=}")
                    else:
                        new_streams.append(stream)

            new_data[channel] = YouTubeChannelData(videos=new_videos,
                                                   streams=new_streams)
    return new_data
