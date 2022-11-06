import asyncio
from asyncio import Queue
from logging import Logger

from pyrogram import Client
from pyrogram.errors import FloodWait, SlowmodeWait

import auxiliary_utils
from format_utils import fmt_pair, fmt_message
from settings import Settings, Profile


async def try_send_message(m: auxiliary_utils.Message,
                           profile: Profile,
                           settings: Settings,
                           client: Client,
                           logger: Logger):
    for i in range(settings.attempt_count):
        try:
            await client.send_message(m.telegram_object.id, fmt_message(m, profile.name))
            await asyncio.sleep(settings.message_delay)
            return
        except (FloodWait, SlowmodeWait) as e:
            logger.warning(e)
            await asyncio.sleep(settings.error_delay)
    else:
        logger.error('Max limit of attempt count')


async def send_worker(q: Queue[auxiliary_utils.MessageGroup],
                      profile: Profile,
                      settings: Settings,
                      client: Client,
                      logger: Logger):
    while True:
        group: auxiliary_utils.MessageGroup = await q.get()
        failed: auxiliary_utils.MessageGroup = []
        if settings.without_sending:
            continue
        logger.info('Sending ...')
        for m in group:
            logger.info(fmt_pair(m.youtube_video, m.telegram_object))
            try:
                await try_send_message(m, profile, settings, client, logger)
            except OSError as e:  # NetworkError (internet access)
                logger.error(f'Send error:\n'
                             f'{fmt_pair(m.youtube_video, m.telegram_object)}\n'
                             f'{e}')
                failed.append(m)
                await asyncio.sleep(settings.error_delay)
        if failed:
            await q.put(failed)
        q.task_done()
        await asyncio.sleep(settings.send_delay)
