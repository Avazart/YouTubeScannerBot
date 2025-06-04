import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ....constants import MAX_CATEGORY_COUNT
from ...bot_types import BotContext, Menu, PageData
from ...keyboards import build_attach_categories_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.callback_query(
    Menu.ATTACH_CATEGORIES, PageData.filter(), F.message.as_("message")
)
async def paginate_attach_categories(
    _query: CallbackQuery,
    message: Message,
    callback_data: PageData,
    state: FSMContext,
    context: BotContext,
):
    data = schemas.StateData(**(await state.get_data()))
    async with context.session_maker.begin() as session:
        data.categories_offset = callback_data.offset
        assert data.channel_id is not None
        keyboard = await build_attach_categories_keyboard(
            data.channel_id,
            data.categories_menu_offset,
            MAX_CATEGORY_COUNT,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)
        await state.set_data(data.model_dump())
