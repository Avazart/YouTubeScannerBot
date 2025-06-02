import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta
from logging import getLogger
from typing import Any

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import or_f
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import (
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .bot_ui.bot_types import BotContext
from .bot_ui.filters import BotAdminFilter, ChatAdminFilter, PrivateChatFilter
from .bot_ui.handlers import bot_admins, chat_admins, chat_users
from .bot_ui.keyboards import video_links_keyboard
from .command_menu import GROUP_COMMANDS, PRIVATE_COMMANDS
from .constants import LAST_DAYS_IN_DB, LAST_DAYS_ON_PAGE, MISFIRE_GRACE_TIME
from .database.models import Destination, YouTubeChannel, YouTubeVideo
from .database.utils import (
    add_forwarded_videos,
    get_active_yt_channels,
    get_forwarding_data,
    get_not_forwarded_videos,
    insert_videos,
)
from .dumpable_memory_storage import DumpableMemoryStorage
from .format_utils import fmt_channel, make_message_text, make_video_line
from .send_worker import try_send_message
from .settings import Settings
from .youtube_parser import search
from .youtube_utils import get_channel_data

logger = getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    logger.info("Bot started.")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(
        PRIVATE_COMMANDS, BotCommandScopeAllPrivateChats()
    )
    await bot.set_my_commands(GROUP_COMMANDS, BotCommandScopeAllGroupChats())


async def run(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    logger.info("Creating a bot instance ...")
    storage: Any
    bot = Bot(token=settings.bot.token.get_secret_value())
    if settings.redis.use:
        logger.info("Connecting to the redis storage ...")
        from aiogram.fsm.storage.redis import ( # pylint: disable=import-outside-toplevel
            RedisStorage,
        )
        from redis.asyncio import (  # pylint: disable=import-outside-toplevel
            from_url,
        )

        redis_client = from_url(settings.redis.url.get_secret_value())
        storage = RedisStorage(redis=redis_client)
    else:
        logger.info("Loading the file storage ...")
        storage = DumpableMemoryStorage(settings.storage_file)
        storage.load()

    dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.USER_IN_TOPIC)

    bot_admin_filter = BotAdminFilter()
    bot_admins.router.callback_query.filter(bot_admin_filter)
    bot_admins.router.message.filter(bot_admin_filter)

    chat_admin_filter = or_f(
        PrivateChatFilter(),  # F.chat.type == 'private' ?
        or_f(bot_admin_filter, ChatAdminFilter()),
    )
    chat_admins.router.message.filter(chat_admin_filter)
    chat_admins.router.callback_query.filter(chat_admin_filter)

    dp.include_routers(
        bot_admins.router,
        chat_admins.router,
        chat_users.router,
    )
    context = BotContext(settings, session_maker)
    logger.info("Creating scheduler ...")
    scheduler = AsyncIOScheduler(timezone=settings.app_tz)
    scan_trigger = CronTrigger.from_crontab(
        settings.scan_schedule, timezone=settings.app_tz
    )
    scheduler.add_job(
        scan,
        args=(session_maker, settings),
        trigger=scan_trigger,
        misfire_grace_time=MISFIRE_GRACE_TIME,
    )
    notify_trigger = CronTrigger.from_crontab(
        settings.notify_schedule, timezone=settings.app_tz
    )
    scheduler.add_job(
        notify,
        args=(session_maker, settings, bot),
        trigger=notify_trigger,
        misfire_grace_time=MISFIRE_GRACE_TIME,
    )
    scheduler.start()
    dp.startup.register(on_startup)
    await dp.start_polling(bot, context=context)



async def scan(session_maker, settings: Settings) -> None:
    async with session_maker() as session:
        channels = await get_active_yt_channels(session)
        logger.info("ChannelMenuData count %d", len(channels))

        logger.info("Scan youtube channels ...")
        videos = await scan_youtube_channels(channels, settings.request_delay)
        recent_videos = get_recent_videos(videos, LAST_DAYS_ON_PAGE)

        logger.info("Recent videos: %d", len(recent_videos))
        # logger.debug(pformat(recent_videos))
        if recent_videos:
            await insert_videos(session, recent_videos)
        logger.info("Scanning complete.")


async def notify(session_maker, settings: Settings, bot: Bot) -> None:
    async with session_maker() as session:
        logger.info("Notification ...")
        dest_with_channels, _ = await get_forwarding_data(session)
        channel_titles = {}
        for channels in dest_with_channels.values():
            for channel in channels:
                channel_titles[channel.id] = channel.title

        for dest, channels in dest_with_channels.items():
            limit = 2 if dest.chat.type == ChatType.CHANNEL else 5
            videos = await get_not_forwarded_videos(
                session, dest, channels, last_days=LAST_DAYS_IN_DB, limit=limit
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
        await add_forwarded_videos(session, dest, dispatched_videos)
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
