import logging
import re
from uuid import uuid4

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    InlineQuery,
    InlineQueryResultVideo,
    InputTextMessageContent,
    Message,
)

from ...database.services import YTVideoService
from ..bot_types import BotContext, VideoLinksData
from ..keyboards import video_links_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)


def parse_number(line: str) -> int:
    if m := re.search(r"^(\d+)", line):
        return int(m.group(1))
    raise RuntimeError("Can`t parse a number")


@router.callback_query(
    VideoLinksData.filter(),
    F.message.as_("message"),
    F.message.html_text.as_("html_text"),
)
async def change_message_preview(
    _query: CallbackQuery,
    message: Message,
    callback_data: VideoLinksData,
    html_text: str,
):
    links = html_text.split("\n")
    links.sort(key=parse_number)
    links.insert(0, links.pop(callback_data.number - 1))
    await message.edit_text(
        "\n".join(links),
        reply_markup=video_links_keyboard(callback_data.number, len(links)),
        parse_mode=ParseMode.HTML,
    )


@router.inline_query()
async def inline_search_handler(query: InlineQuery, context: BotContext):
    text = query.query.strip()
    if not text:
        return

    async with context.session_maker() as session:
        service = YTVideoService(session)
        videos = await service.search(text, limit=10)

        articles = []
        for video in videos:
            text = f"{video.channel.title}\n{video.title}\n{video.url}"
            articles.append(
                InlineQueryResultVideo(
                    id=str(uuid4()),
                    video_url=video.url,
                    mime_type="text/html",
                    title=video.title,
                    description=video.channel.title,
                    thumbnail_url=video.preview_url,
                    input_message_content=InputTextMessageContent(
                        message_text=text
                    ),
                )
            )
    await query.answer(articles, cache_time=1)
