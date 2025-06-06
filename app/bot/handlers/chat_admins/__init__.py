from aiogram import Router

from .attach_category_menu import router as attach_categories_router
from .category_menu import router as category_menu_router
from .channel_menu import router as channel_menu_router
from .common import router as common_menu_router
from .main_menu import router as main_menu_router
from .telegrams_menu import router as telegram_menu_router

router = Router(name=__name__)
router.include_routers(
    main_menu_router,
    category_menu_router,
    channel_menu_router,
    attach_categories_router,
    telegram_menu_router,
    common_menu_router,
)


__all__ = ["router"]
