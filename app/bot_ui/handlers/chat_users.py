import logging
import re

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery

from ..bot_types import VideoLinksData
from ..keyboards import video_links_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)


def parse_number(line: str) -> int | None:
    if m := re.search(r"^(\d+)", line):
        return int(m.group(1))
    return None


@router.callback_query(
    VideoLinksData.filter(),
    F.message.html_text.as_("html_text"),
)
async def change_message_preview(
    callback_query: CallbackQuery,
    callback_data: VideoLinksData,
    html_text: str,
):
    links = html_text.split("\n")
    links.sort(key=parse_number)
    links.insert(0, links.pop(callback_data.number - 1))
    await callback_query.message.edit_text(
        "\n".join(links),
        reply_markup=video_links_keyboard(callback_data.number, len(links)),
        parse_mode=ParseMode.HTML,
    )
    await callback_query.answer()
