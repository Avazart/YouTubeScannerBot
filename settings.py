from dataclasses import dataclass
from pathlib import Path

VIEWS_SCRIPT_PATH = Path('views.sql')
BACKUP_FILE_PATH = Path('../backup_debug.json')
LOG_CONFIG_FILE_PATH_FMT = 'configs/log_config{}.json'
MIN_MEMBER_COUNT = 10

LAST_DAYS_ON_PAGE = 2
LAST_DAYS_IN_DB = 30

KEYBOARD_COLUMN_COUNT = 4

MAX_YT_CHANNEL_COUNT = 10
MAX_TAG_COUNT = 40
MAX_TG_COUNT = 10


@dataclass(frozen=True)
class Settings:
    token: str
    bot_admin_ids: frozenset[int]

    work_dir: Path
    database_url: str

    redis_url: str
    redis_queue: str = "youtube_scanner:queue"

    debug: bool = False
    without_sending: bool = False

    cron_schedule: str = '*/30 * * * *'
    request_delay: float = 1
    send_delay: float = 5 * 60
    error_delay: float = 65
    message_delay: float = 1
    attempt_count: int = 3
