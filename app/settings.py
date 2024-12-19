from typing import Annotated, Final

import pytz
from pydantic import BaseModel, BeforeValidator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logging_utils import LogSettings

MIN_MEMBER_COUNT: Final[int] = 10

LAST_DAYS_ON_PAGE: Final[int] = 7
LAST_DAYS_IN_DB: Final[int] = 7

KEYBOARD_COLUMN_COUNT: Final[int] = 4

MAX_YT_CHANNEL_COUNT: Final[int] = 10
MAX_CATEGORY_COUNT: Final[int] = 40
MAX_TG_COUNT: Final[int] = 10
MISFIRE_GRACE_TIME: Final[int] = 10 * 60


class BotSettings(BaseModel):
    token: SecretStr
    admin_ids: frozenset[int]


class RedisSettings(BaseModel):
    use: bool
    url: SecretStr
    queue: str = "youtube_scanner:queue"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    log: LogSettings
    bot: BotSettings
    redis: RedisSettings
    storage_file: str
    database_url: str

    without_sending: bool = False
    scan_schedule: str = "*/30 * * * *"
    notify_schedule: str = "*/30 * * * *"

    request_delay: float = 1
    send_delay: float = 5 * 60
    error_delay: float = 65
    message_delay: float = 0.5
    attempt_count: int = 3
    app_tz: Annotated[pytz.BaseTzInfo, BeforeValidator(pytz.timezone)]
    parse_tags: bool = False
