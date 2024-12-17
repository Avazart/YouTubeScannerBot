from typing import Final

from aiogram.types import BotCommand

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
