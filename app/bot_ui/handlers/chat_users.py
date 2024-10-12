import logging
from collections import deque

from aiogram import Router
from aiogram.types import CallbackQuery

from ..bot_types import VideoLinksData
from ..keyboards import video_links_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.callback_query(VideoLinksData.filter())
async def rotate_video_links(
    callback_query: CallbackQuery,
    callback_data: VideoLinksData,
):
    links = deque(callback_query.message.text.split("\n"))
    links.rotate(int(callback_data.direction))
    await callback_query.message.edit_text(
        "\n".join(links),
        reply_markup=video_links_keyboard(),
    )
    await callback_query.answer()
