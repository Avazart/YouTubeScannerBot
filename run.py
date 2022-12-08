import asyncio
import itertools
import random
from asyncio import Queue
from datetime import datetime, timedelta
from logging import Logger
from typing import Sequence

import httpcore
from aiogram import Dispatcher, Bot
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from bot_ui.callbacks import register_callback_queries
from bot_ui.commands import register_commands
from bot_ui.filers import ChatAdminFilter, BotAdminFilter
from backup_utils import import_data
from bot_ui.bot_types import BotContext, Storage
from database.models import YouTubeChannel, Base, YouTubeVideo
from database.utils import get_forwarding_data, get_last_video_ids, get_video_by_original_id, create_views
from format_utils import fmt_scan_data, fmt_groups, fmt_channel
from youtube_utils import get_channel_data, ScanData, YouTubeChannelData
from send_worker import send_worker
from message_utils import (
    MessageGroup,
    load_message_queue,
    save_message_queue,
    get_tg_to_yt_videos,
    make_message_groups
)
from settings import (
    Profile,
    Settings,
    DB_STRING_FMT,
    DB_NAME,
    QUEUE_FILE_PATH,
    VIEWS_SCRIPT_PATH,
    BACKUP_FILE_PATH,
    LAST_DAYS_IN_DB,
    LAST_DAYS_ON_PAGE
)


async def run(profile: Profile, settings: Settings, logger: Logger):
    last_time = datetime.today() - timedelta(days=LAST_DAYS_ON_PAGE)
    q: Queue[MessageGroup] = load_message_queue(profile.work_dir / QUEUE_FILE_PATH, last_time)
    try:
        engine = create_async_engine(DB_STRING_FMT.format(profile.work_dir / DB_NAME), echo=False)
        SessionMaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        if not (profile.work_dir / DB_NAME).exists():
            async with engine.begin() as connection:
                logger.debug('Creating database ..')
                await connection.run_sync(Base.metadata.create_all)
                if VIEWS_SCRIPT_PATH.exists():
                    logger.debug('Creating views ..')
                    await create_views(VIEWS_SCRIPT_PATH, connection)
            if BACKUP_FILE_PATH.exists():
                logger.debug('Import callback_data from backup file ...')
                await import_data(BACKUP_FILE_PATH, SessionMaker)

        bot = Bot(token=profile.token)
        dp = Dispatcher()

        bot_admin_ids = {profile.owner_id, }

        bot_admin_filter = BotAdminFilter(bot_admin_ids)
        chat_admin_filter = ChatAdminFilter(bot_admin_ids)

        register_commands(dp, chat_admin_filter, bot_admin_filter)
        register_callback_queries(dp, chat_admin_filter, bot_admin_filter)

        context = BotContext(logger, SessionMaker, profile, Storage())
        tasks = [
            dp.start_polling(bot, skip_updates=True, context=context),
            update_loop(q, SessionMaker, settings, logger),
            send_worker(q, settings, bot, logger),
        ]
        await asyncio.gather(*tasks)

    except asyncio.exceptions.CancelledError:
        pass
    finally:
        if not q.empty():
            logger.info('Save queue ...')
            save_message_queue(profile.work_dir / QUEUE_FILE_PATH, q)


async def update_loop(q: Queue[MessageGroup],
                      SessionMaker,
                      settings: Settings,
                      logger: Logger):
    if not q.empty():
        logger.info('Waiting ...')
        await asyncio.sleep(settings.update_interval)

    while True:
        async with SessionMaker.begin() as session:
            await update(q, session, settings, logger)
        logger.info('Waiting ...')
        await asyncio.sleep(settings.update_interval)


async def update(q: Queue[MessageGroup],
                 session: AsyncSession,
                 settings: Settings,
                 logger: Logger):

    logger.info('Updating ...')
    tg_to_yt_channels, tg_yt_to_forwarding = await get_forwarding_data(session)
    youtube_channels = list(set(itertools.chain.from_iterable(tg_to_yt_channels.values())))
    random.shuffle(youtube_channels)
    logger.debug(f'Channel count {len(youtube_channels)}')

    logger.info('Scan youtube channels ...')
    scan_data = await scan_youtube_channels(youtube_channels, settings.request_delay, logger)

    logger.info('Search new videos ...')
    new_data = await get_new_data(scan_data, session, logger)
    new_videos = frozenset(itertools.chain.from_iterable(list(new_data.values())))

    logger.info(f'New videos: {len(new_videos)}')
    if new_videos:
        logger.info(fmt_scan_data(new_data))

        logger.info('Make message groups ...')
        tg_to_yt_videos = get_tg_to_yt_videos(new_data, tg_to_yt_channels)
        groups = make_message_groups(tg_to_yt_videos, youtube_channels)
        for group in groups:
            await q.put(group)
        if groups:
            logger.info('Messages:\n' + fmt_groups(groups, ' ' * 4))

        logger.info('Save new videos to database ...')
        try:
            session.add_all(new_videos)
            await session.commit()
        except Exception as e:
            logger.exception(e)


async def scan_youtube_channels(channels: Sequence[YouTubeChannel],
                                request_delay: float,
                                logger: Logger) -> ScanData:
    result = {}
    for i, channel in enumerate(channels, start=1):
        logger.debug(f"{i}/{len(channels)} " + fmt_channel(channel))
        try:
            result[channel] = await get_channel_data(channel)
        except (httpcore.NetworkError, httpcore.TimeoutException) as e:
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
        new_videos = []
        new_streams = []

        if data.videos or data.streams:
            last_video_ids = await get_last_video_ids(channel.id, LAST_DAYS_IN_DB, session)

            # /videos
            videos = filter_by_time(data.videos)
            for video in videos:
                if video.original_id not in last_video_ids:
                    new_videos.append(video)

            # /streams
            streams = filter_by_time(data.streams)
            for stream in streams:
                if stream.original_id not in last_video_ids:
                    if exist_stream := await get_video_by_original_id(stream.original_id, session):
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
