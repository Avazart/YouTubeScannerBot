import asyncio
import pickle
from logging import Logger

import redis.asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError

from .message_utils import ScannerMessage, MessageGroup
from .format_utils import fmt_pair, fmt_message
from .settings import Settings


async def try_send_message(m: ScannerMessage,
                           settings: Settings,
                           bot: Bot,
                           logger: Logger):
    for i in range(settings.attempt_count):
        try:
            await bot.send_message(
                chat_id=m.destination.chat.original_id,
                text=fmt_message(m),
                message_thread_id=m.destination.get_thread_original_id(),
                parse_mode='HTML'
            )
            await asyncio.sleep(settings.message_delay)
            return
        except TelegramRetryAfter as e:
            logger.warning(e)
            await asyncio.sleep(settings.error_delay)
    else:
        logger.error('Max limit of attempt count')


async def send_worker(settings: Settings,
                      bot: Bot,
                      logger: Logger):
    while True:
        async with redis.asyncio.from_url(settings.redis_url) as redis_client:
            _, data = await redis_client.blpop(settings.redis_queue)
            group: MessageGroup = pickle.loads(data)
            failed: MessageGroup = []
            logger.info('Sending ...')
            for m in group:
                logger.info(fmt_pair(m.youtube_video, m.destination))
                try:
                    if not settings.without_sending:
                        await try_send_message(m, settings, bot, logger)
                except TelegramNetworkError as e:
                    logger.error(
                        'Send error:\n'
                        f'{fmt_pair(m.youtube_video, m.destination)}\n'
                        f'{e} {type(e)}'
                    )
                    failed.append(m)
                    await asyncio.sleep(settings.error_delay)
                except Exception as e:
                    # TODO aiogram.exceptions.TelegramBadRequest:
                    #  Bad Request: chat not found
                    logger.exception(e)

            if failed:
                dumps = [pickle.dumps(f) for f in failed]
                await redis_client.rpush(settings.redis_url, *dumps)

        await asyncio.sleep(settings.send_delay)
