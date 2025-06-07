from logging import getLogger

from aiogram import Bot, Dispatcher
from aiogram.filters import or_f
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import (
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .bot.bot_types import BotContext
from .bot.filters import BotAdminFilter, ChatAdminFilter, PrivateChatFilter
from .bot.handlers import bot_admins, chat_admins, chat_users
from .constants import GROUP_COMMANDS, MISFIRE_GRACE_TIME, PRIVATE_COMMANDS
from .dumpable_memory_storage import DumpableMemoryStorage
from .jobs import notify, scan
from .logging_utils import decorate_router_handlers
from .settings import Settings

logger = getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    logger.info("Bot started.")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(
        PRIVATE_COMMANDS, BotCommandScopeAllPrivateChats()
    )
    await bot.set_my_commands(GROUP_COMMANDS, BotCommandScopeAllGroupChats())


async def create_storage(settings: Settings) -> BaseStorage:
    if settings.redis.use:
        logger.info("Connecting to the redis storage ...")
        from aiogram.fsm.storage.redis import (  # pylint: disable=import-outside-toplevel
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
    return storage


def create_scheduler(
    session_maker,
    settings: Settings,
    bot: Bot,
) -> AsyncIOScheduler:
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
    return scheduler


def create_dispatcher(storage: BaseStorage) -> Dispatcher:
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
    return dp


async def run(settings: Settings) -> None:
    logger.info("Creating a database engine ...")
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    logger.info("Creating a bot instance ...")
    bot = Bot(token=settings.bot.token.get_secret_value())

    storage = await create_storage(settings)
    dispatcher = create_dispatcher(storage)
    dispatcher.startup.register(on_startup)
    decorate_router_handlers(dispatcher)

    context = BotContext(settings, session_maker)
    if "without_scheduler" not in settings.flags:
        logger.info("Creating scheduler ...")
        scheduler = create_scheduler(session_maker, settings, bot)
        scheduler.start()
    try:
        await dispatcher.start_polling(bot, context=context)
    finally:
        if isinstance(storage, DumpableMemoryStorage):
            storage.dump()
