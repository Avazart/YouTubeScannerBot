import asyncio
from logging import getLogger

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter

from .settings import Settings

logger = getLogger(__name__)


async def try_send_message(
    bot: Bot,
    chat_id: int | str,
    text: str,
    settings: Settings,
    **kwargs,
) -> bool:
    for _ in range(settings.attempt_count):
        try:
            if not settings.without_sending:
                await bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return True
        except TelegramRetryAfter as e:
            logger.warning(e)
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            logger.error(e)
            return False
    else:
        logger.error("Max limit of attempt count")
    return False
