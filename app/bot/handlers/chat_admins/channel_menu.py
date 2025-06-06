import logging

from aiogram import F, Router
from aiogram.client.bot import User
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ....constants import MAX_YT_CHANNEL_COUNT
from ....database.services import TelegramService
from ....database.services.forwarding_service import ForwardingService
from ...bot_types import BotContext, ChannelsMenuData, Menu, PageData
from ...keyboards import ChannelData, build_channel_keyboard
from ...state_history import StateHistory

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.callback_query(
    Menu.CATEGORIES,
    ChannelsMenuData.filter(),  # Apply
    F.message.as_("message"),
    F.from_user.as_("from_user"),
)
async def show_channels_menu(
    _query: CallbackQuery,
    state: FSMContext,
    message: Message,
    from_user: User,
    context: BotContext,
):
    data = await state.get_data()
    history = StateHistory.from_list(data.get("history", []))
    chat_id = data["chat_id"]
    thread_id = data["thread_id"]
    channel_offset = data.get("channel_offset", 0)
    category_selection = data.get("category_selection", [])

    async with context.session_maker.begin() as session:
        keyboard = await build_channel_keyboard(
            chat_id,
            thread_id,
            from_user.id in context.settings.bot.admin_ids,
            channel_offset,
            MAX_YT_CHANNEL_COUNT,
            category_selection,
            session,
        )
        await message.edit_text("YouTube channels:", reply_markup=keyboard)

    history.append(Menu.CHANNELS)
    await state.update_data(
        {
            "history": history.as_list(),
            "channel_offset": channel_offset,
            "category_selection": category_selection,
        }
    )
    await state.set_state(Menu.CHANNELS)


@router.callback_query(
    Menu.CHANNELS,
    ChannelData.filter(),
    F.message.as_("message"),
    F.from_user.as_("from_user"),
)
async def channel_checked(
    _query: CallbackQuery,
    message: Message,
    from_user: User,
    callback_data: ChannelData,
    context: BotContext,
    state: FSMContext,
):
    data = await state.get_data()
    chat_id = data["chat_id"]
    thread_id = data["thread_id"]
    channel_offset = data.get("channel_offset", 0)
    category_selection = data.get("category_selection", [])

    async with context.session_maker.begin() as session:
        assert chat_id is not None
        tg_service = TelegramService(session)
        forwarding_service = ForwardingService(session)
        if tg := await tg_service.get(chat_id, thread_id):
            if not callback_data.enabled:
                await forwarding_service.add(
                    callback_data.id, tg.chat.original_id, tg.get_thread_id()
                )
            else:
                await forwarding_service.remove(
                    callback_data.id, tg.chat.original_id, tg.get_thread_id()
                )
            is_bot_admin = from_user.id in context.settings.bot.admin_ids
            keyboard = await build_channel_keyboard(
                tg.chat.original_id,
                tg.get_thread_original_id(),
                is_bot_admin,
                channel_offset,
                MAX_YT_CHANNEL_COUNT,
                category_selection,
                session,
            )
            await message.edit_reply_markup(reply_markup=keyboard)
        else:
            logger.warning(
                "chat_id %s, thread_id %s not found", chat_id, thread_id
            )

    await state.update_data(
        {
            "channel_offset": channel_offset,
            "category_selection": category_selection,
        }
    )


@router.callback_query(
    Menu.CHANNELS,
    PageData.filter(),
    F.message.as_("message"),
    F.from_user.as_("from_user"),
)
async def paginate_channels(
    _query: CallbackQuery,
    message: Message,
    from_user: User,
    callback_data: PageData,
    state: FSMContext,
    context: BotContext,
):
    data = await state.get_data()
    chat_id = data["chat_id"]
    thread_id = data["thread_id"]
    channel_offset = callback_data.offset
    category_selection = data.get("category_selection", [])

    is_bot_admin = from_user.id in context.settings.bot.admin_ids
    async with context.session_maker.begin() as session:
        keyboard = await build_channel_keyboard(
            chat_id,
            thread_id,
            is_bot_admin,
            channel_offset,
            MAX_YT_CHANNEL_COUNT,
            category_selection,
            session,
        )
        await message.edit_reply_markup(reply_markup=keyboard)

    await state.update_data(
        {
            "channel_offset": channel_offset,
            "category_selection": category_selection,
        }
    )
