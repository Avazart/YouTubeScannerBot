import logging

from aiogram import F, Router
from aiogram.filters import or_f
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Chat, Message

from ....constants import MAX_CATEGORY_COUNT
from ...bot_types import BotContext, CategoryData, Menu, PageData
from ...keyboards import CategoriesMenuData, build_category_filter_keyboard
from ...state_history import StateHistory

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.callback_query(
    or_f(Menu.MAIN, Menu.TELEGRAMS),
    CategoriesMenuData.filter(),
    F.message.as_("message"),
    F.message.chat.as_("chat"),
)
async def show_categories_menu(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    chat: Chat,
    context: BotContext,
):
    data = await state.get_data()
    history = StateHistory.from_list(data["history"])
    category_offset = data["category_offset"]
    category_selection = data["category_selection"]

    async with context.session_maker.begin() as session:
        keyboard = await build_category_filter_keyboard(
            category_offset,
            MAX_CATEGORY_COUNT,
            category_selection,
            session,
        )
        await message.edit_text(
            "Select categories for filter youtube channels:",
            reply_markup=keyboard,
        )
    history.append(Menu.CATEGORIES)
    await state.update_data({"history": history.as_list()})
    await state.set_state(Menu.CATEGORIES)


@router.callback_query(
    Menu.CATEGORIES, CategoryData.filter(), F.message.as_("message")
)
async def category_button_pressed(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    callback_data: CategoryData,
    context: BotContext,
):
    data = await state.get_data()
    category_offset = data["category_offset"]
    category_selection = data["category_selection"]

    if callback_data.id in category_selection:
        category_selection.remove(callback_data.id)
    else:
        category_selection.append(callback_data.id)

    async with context.session_maker.begin() as session:
        keyboard = await build_category_filter_keyboard(
            category_offset,
            MAX_CATEGORY_COUNT,
            category_selection,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)

    await state.update_data({"category_selection": category_selection})


@router.callback_query(
    Menu.CATEGORIES, PageData.filter(), F.message.as_("message")
)
async def paginate_categories(
    _query: CallbackQuery,
    message: Message,
    callback_data: PageData,
    state: FSMContext,
    context: BotContext,
):
    data = await state.get_data()
    category_offset = callback_data.offset
    category_selection = data["category_selection"]

    async with context.session_maker.begin() as session:
        keyboard = await build_category_filter_keyboard(
            category_offset,
            MAX_CATEGORY_COUNT,
            category_selection,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)

    await state.update_data({"category_offset": category_offset})
