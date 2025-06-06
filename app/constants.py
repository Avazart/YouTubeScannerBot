from typing import Final

from aiogram.types import BotCommand

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


PRIVATE_COMMANDS: Final[list] = [
    BotCommand(
        command="/start",
        description="Start working with the bot",
    ),
    BotCommand(
        command="/menu",
        description="Open the menu",
    ),
    BotCommand(
        command="/add_channel",
        description="Add youtube channel",
    ),
    BotCommand(
        command="/remove_channel",
        description="Remove youtube channel",
    ),
    BotCommand(
        command="/add_category",
        description="Add category for youtube channel",
    ),
    BotCommand(
        command="/remove_category",
        description="Remove category by name",
    ),
]

GROUP_COMMANDS: Final[list] = [
    BotCommand(
        command="/menu",
        description="Open the menu",
    ),
]
