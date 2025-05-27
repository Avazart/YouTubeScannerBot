from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import BaseModel, BeforeValidator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logging_utils import LogSettings

TimeZone = Annotated[ZoneInfo, BeforeValidator(ZoneInfo)]


class BotSettings(BaseModel):
    token: SecretStr
    admin_ids: frozenset[int]


class RedisSettings(BaseModel):
    use: bool
    url: SecretStr
    queue: str = "youtube_scanner:queue"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")

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
    app_tz: TimeZone
    parse_tags: bool = False
