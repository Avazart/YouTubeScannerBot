from pathlib import Path
from typing import Any

import tzlocal
from pydantic import BaseSettings, Field

MIN_MEMBER_COUNT = 10

LAST_DAYS_ON_PAGE = 2
LAST_DAYS_IN_DB = 30

KEYBOARD_COLUMN_COUNT = 4

MAX_YT_CHANNEL_COUNT = 10
MAX_TAG_COUNT = 40
MAX_TG_COUNT = 10


def _local_tz():
    return str(tzlocal.get_localzone())


def _parse_ids(s: str) -> frozenset[int]:
    return frozenset(map(int, s.split(',')))


class Settings(BaseSettings):
    bot_token: str
    bot_admin_ids: frozenset[int]

    log_dir: Path
    database_url: str

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
    check_migrations: bool = True

    class Config:
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name == 'bot_admin_ids':
                return _parse_ids(raw_val)
            return getattr(cls, 'json_loads')(raw_val)
