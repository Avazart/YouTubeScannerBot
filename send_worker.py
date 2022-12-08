import asyncio
from asyncio import Queue
from logging import Logger

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError

import message_utils
from format_utils import fmt_pair, fmt_message
from settings import Settings


async def try_send_message(m:  message_utils.ScannerMessage,
                           settings: Settings,
                           bot: Bot,
                           logger: Logger):
    for i in range(settings.attempt_count):
        try:
            await bot.send_message(chat_id=m.destination.chat.original_id,
                                   text=fmt_message(m),
                                   message_thread_id=m.destination.get_thread_original_id(),
                                   parse_mode='HTML')
            await asyncio.sleep(settings.message_delay)
            return
        except TelegramRetryAfter as e:
            logger.warning(e)
            await asyncio.sleep(settings.error_delay)
    else:
        logger.error('Max limit of attempt count')


async def send_worker(q: Queue[message_utils.MessageGroup],
                      settings: Settings,
                      bot: Bot,
                      logger: Logger):
    while True:
        group: message_utils.MessageGroup = await q.get()
        failed: message_utils.MessageGroup = []
        logger.info('Sending ...')
        for m in group:
            logger.info(fmt_pair(m.youtube_video, m.destination))
            try:
                if not settings.without_sending:
                    await try_send_message(m, settings, bot, logger)
            except TelegramNetworkError as e:
                logger.error(f'Send error:\n'
                             f'{fmt_pair(m.youtube_video, m.destination)}\n'
                             f'{e} {type(e)}')
                failed.append(m)
                await asyncio.sleep(settings.error_delay)
            except Exception as e:
                # aiogram.exceptions.TelegramBadRequest: Bad Request: chat not found
                logger.exception(e)
        if failed:
            await q.put(failed)
        q.task_done()
        await asyncio.sleep(settings.send_delay)
