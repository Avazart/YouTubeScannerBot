import asyncio
import csv
import itertools
import json
import random
import sys
from asyncio import Queue
from dataclasses import asdict
from datetime import datetime, timedelta
from logging import getLogger, Logger
from logging.config import dictConfig
from pathlib import Path
from typing import Sequence

import click
import colorama
import httpcore
import httpx
from pyrogram import Client
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import click_utils
from auxiliary_utils import MessageGroup, load_queue, save_queue, make_message_groups
from database_models import Base, TelegramObject, YouTubeChannel
from database_utils import (
    ForwardingData,
    get_forwarding_data,
    get_last_video_ids,
    telegram_object_by_user_name,
    add_forwarding,
    create_views
)
from youtube_utils import ScanData, get_channel_videos, get_channel_info
from format_utils import fmt_scan_data, fmt_channel, fmt_groups
from send_worker import send_worker
from settings import (
    Profile,
    Settings,
    DB_STRING_FMT,
    DB_NAME,
    LAST_VIDEO_COUNT,
    QUEUE_FILE_PATH,
    VIEWS_SCRIPT_PATH,
    LOG_CONFIG_FILE_PATH_FMT
)


def init_logging(workdir: Path):
    logs_path = workdir / 'logs'
    logs_path.mkdir(parents=True, exist_ok=True)
    log_config_path = LOG_CONFIG_FILE_PATH_FMT.format('_debug' if __debug__ else '')
    with open(log_config_path) as file:
        config = json.load(file)
        file_handler = config['handlers']['FileHandler']
        file_handler['filename'] = str(logs_path / 'log.txt')
        dictConfig(config)


async def run(profile: Profile, settings: Settings, logger: Logger):
    last_time = datetime.today() - timedelta(days=settings.last_days)
    q: Queue[MessageGroup] = load_queue(profile.workdir / QUEUE_FILE_PATH, last_time)
    try:
        engine = create_async_engine(DB_STRING_FMT.format(profile.workdir / DB_NAME), echo=False)
        SessionMaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with Client(**asdict(profile)) as client:
            if not (profile.workdir / DB_NAME).exists():
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
                    await create_views(VIEWS_SCRIPT_PATH, connection)

                async with SessionMaker.begin() as session:
                    await update_tg_info(client, session)

            asyncio.create_task(send_worker(q, settings, client, logger))
            if not q.empty():
                logger.info('Waiting ...')
                await asyncio.sleep(settings.update_interval)

            while True:
                async with SessionMaker.begin() as session:
                    await update(q, session, settings, logger)
                logger.info('Waiting ...')
                await asyncio.sleep(settings.update_interval)
    finally:
        if not q.empty():
            logger.info('Save queue ...')
            save_queue(profile.workdir / QUEUE_FILE_PATH, q)


async def recreate_db(profile: Profile):
    engine = create_async_engine(DB_STRING_FMT.format(profile.workdir / DB_NAME), echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
        await create_views(VIEWS_SCRIPT_PATH, connection)

    async with Client(**asdict(profile)) as client:
        SessionMaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with SessionMaker.begin() as session:
            await update_tg_info(client, session)


async def import_from_csv(profile: Profile, file_name: str):
    engine = create_async_engine(DB_STRING_FMT.format(profile.workdir / DB_NAME), echo=False)
    SessionMaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionMaker.begin() as session:
        with open(file_name, 'r', encoding='utf-8', newline='') as file:
            reader = csv.reader(file, delimiter=';', quotechar='"', dialect='excel')
            for row in reader:
                await work_with_csv_row(row, session)


async def work_with_csv_row(row: Sequence[str], session: AsyncSession):
    if len(row) >= 2 and not row[0].startswith('#'):
        yt_channel_url = row[0].strip()
        enabled = len(row) == 3 and row[2].strip().lower() in ('1', 'true', 'on')

        try:
            channel: YouTubeChannel = await get_channel_info(yt_channel_url)
        except httpx.HTTPError as e:
            raise RuntimeError(str(e))

        try:
            tg_id = int(row[1])
            tg = TelegramObject(id=tg_id)
        except ValueError:
            tg_name = row[1].strip()
            tg = await telegram_object_by_user_name(tg_name, session)

        if tg:
            await add_forwarding(channel, tg, enabled, session)
        else:
            raise RuntimeError('Wrong telegram id or telegram username!')


async def update_tg_info(client: Client, session: AsyncSession):
    tgs = []
    async for dialog in client.get_dialogs():
        tgs.append(
            TelegramObject(id=dialog.chat.id,
                           type=dialog.chat.type.name,
                           user_name=dialog.chat.username,
                           title=dialog.chat.title,
                           first_name=dialog.chat.first_name,
                           last_name=dialog.chat.last_name)
        )
    tgs = filter(lambda tg_: tg_.type not in ('PRIVATE', 'BOT'), tgs)
    for tg in tgs:
        await session.merge(tg)
    await session.commit()


async def scan_youtube_channels(channels,
                                request_delay: float,
                                logger: Logger) -> ScanData:
    result = {}
    for channel in channels:
        logger.debug(fmt_channel(channel))
        try:
            result[channel] = await get_channel_videos(channel)
        except (httpcore.NetworkError, httpcore.TimeoutException) as e:
            logger.error(f'Scan error {channel.videos_url}\n{type(e)}')
        await asyncio.sleep(request_delay)
    return result


async def get_new_video_data(scan_data: ScanData,
                             last_days: int,
                             session: AsyncSession) -> ScanData:
    new_data: ScanData = {}
    last_time = datetime.today() - timedelta(days=last_days)
    for channel, videos in scan_data.items():
        videos = list(filter(lambda v: v.creation_time >= last_time, videos))
        if videos:
            last_video_ids = await get_last_video_ids(channel.id,
                                                      LAST_VIDEO_COUNT,
                                                      last_days,
                                                      session)
            videos = {video.id: video for video in videos}
            new_videos_ids = set(videos.keys()) - set(last_video_ids)
            new_videos = [videos[video_id] for video_id in new_videos_ids]
            if new_videos:
                new_data[channel] = new_videos
    return new_data


async def update(q: Queue[MessageGroup],
                 session: AsyncSession,
                 settings: Settings,
                 logger: Logger):
    logger.info('Updating ...')

    forwarding: ForwardingData = await get_forwarding_data(session,
                                                           not settings.without_sending)
    youtube_channels = list(set(itertools.chain.from_iterable(forwarding.values())))
    random.shuffle(youtube_channels)
    youtube_channel_titles = {c.id: c.title for c in youtube_channels}

    logger.info('Scan youtube channels ...')
    scan_data = await scan_youtube_channels(youtube_channels, settings.request_delay, logger)

    logger.info('Search new videos ...')
    new_data = await get_new_video_data(scan_data, settings.last_days, session)
    new_videos = set(itertools.chain.from_iterable(new_data.values()))

    logger.info(f'New videos: {len(new_videos)}')
    if new_data:
        logger.info(fmt_scan_data(new_data))
        logger.info('Make message groups ...')
        groups = make_message_groups(new_data, forwarding, youtube_channel_titles)
        for group in groups:
            await q.put(group)
        if groups:
            logger.info('Messages:\n' + fmt_groups(groups, ' ' * 4))
        logger.info('Save new videos to database ...')
        session.add_all(new_videos)


@click.group(invoke_without_command=True)
@click_utils.option_class(Profile)
@click.pass_context
def command_group(context, profile: Profile):
    if not profile.workdir.exists():
        profile.workdir.mkdir()
    init_logging(profile.workdir)
    context.obj['logger'] = getLogger('main')
    context.obj['profile'] = profile
    if context.invoked_subcommand is None:
        context.invoke(command_run)


@command_group.command(name='run')
@click_utils.option_class(Settings)
@click.pass_context
@click_utils.log_work_process('main')
def command_run(context, settings: Settings):
    profile: Profile = context.obj['profile']
    logger: Logger = context.obj['logger']
    asyncio.run(run(profile, settings, logger))


@command_group.command(name='recreate_db')
@click.pass_context
@click_utils.log_work_process('main')
def command_recreate_db(context):
    profile: Profile = context.obj['profile']
    asyncio.run(recreate_db(profile))


@command_group.command(name='import')
@click.argument('file_name', required=True)
@click.pass_context
@click_utils.log_work_process('main')
def command_import(context, file_name: str):
    profile: Profile = context.obj['profile']
    asyncio.run(import_from_csv(profile, file_name))


def startup():
    colorama.init()
    random.seed()

    if sys.platform.startswith('win'):
        from win_console_utils import init_win_console

        init_win_console()
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    command_group.main(obj={}, standalone_mode=False)


if __name__ == '__main__':
    startup()
