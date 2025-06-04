from typing import Final

MIN_MEMBER_COUNT: Final[int] = 10

LAST_DAYS_ON_PAGE: Final[int] = 7
LAST_DAYS_IN_DB: Final[int] = 7

KEYBOARD_COLUMN_COUNT: Final[int] = 4

MAX_YT_CHANNEL_COUNT: Final[int] = 10
MAX_CATEGORY_COUNT: Final[int] = 40
MAX_TG_COUNT: Final[int] = 10
MISFIRE_GRACE_TIME: Final[int] = 10 * 60


BOT_DESCRIPTION: Final[str] = (
    "I periodically scan YouTube channels "
    "for new videos and send you links to them in Telegram\n\n"
    "You can control me by sending these commands:\n\n"
    "/menu - open the menu\n\n"
    "/add_channel <url> - add youtube channel"
)
