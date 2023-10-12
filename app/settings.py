from pathlib import Path
from typing import Any, Final

import tzlocal
from aiogram.types import BotCommand
from pydantic import BaseSettings, Field

MIN_MEMBER_COUNT: Final[int] = 10

LAST_DAYS_ON_PAGE: Final[int] = 2
LAST_DAYS_IN_DB: Final[int] = 30

KEYBOARD_COLUMN_COUNT: Final[int] = 4

MAX_YT_CHANNEL_COUNT: Final[int] = 10
MAX_TAG_COUNT: Final[int] = 40
MAX_TG_COUNT: Final[int] = 10

MY_COMMANDS: Final[list] = [
    BotCommand(command='/start', description='Start working with the bot'),
    BotCommand(command='/menu', description='Open the menu'),
    BotCommand(command='/add_channel', description='Add youtube channel'),
    BotCommand(command='/remove_channel',
               description='Remove youtube channel'),
    BotCommand(command='/add_tag', description='Add tag for youtube channel'),
    BotCommand(command='/remove_tag', description='Remove tag by name')
]


def _local_tz():
    return str(tzlocal.get_localzone())


def _parse_ids(s: str) -> frozenset[int]:
    return frozenset(map(int, s.split(',')))


class Settings(BaseSettings):
    bot_token: str
    bot_admin_ids: frozenset[int]

    log_dir: Path

    db_password: str = Field(env="PGPASSWORD")
    db_user: str = Field("postgres", env="PGUSER")
    db_name: str = Field("postgres", env="PGDATABASE")
    db_host: str = Field("localhost", env="PGHOST")
    db_port: int = Field(5432, env="PGPORT")

    redis_url: str
    redis_queue: str = "youtube_scanner:queue"

    mode: str = 'dev'
    without_sending: bool = False

    cron_schedule: str = '*/30 * * * *'
    request_delay: float = 1
    send_delay: float = 5 * 60
    error_delay: float = 65
    message_delay: float = 1
    attempt_count: int = 3
    tz: str = Field(default_factory=_local_tz)
    check_migrations: bool = False
    db_url_fmt = ("postgresql+asyncpg://{user}:{password}"
                  "@{host}:{port}/{db_name}")

    class Config:
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name == 'bot_admin_ids':
                return _parse_ids(raw_val)
            return getattr(cls, 'json_loads')(raw_val)

    @property
    def database_url(self):
        return self.db_url_fmt.format(
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            db_name=self.db_name
        )
