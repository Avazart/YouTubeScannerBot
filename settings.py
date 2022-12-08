from dataclasses import dataclass
from pathlib import Path

DB_NAME = 'database.sqlite'
DB_STRING_FMT = 'sqlite+aiosqlite:///{}'
VIEWS_SCRIPT_PATH = Path('views.sql')
QUEUE_FILE_PATH = Path('queue.pickle')
BACKUP_FILE_PATH = Path('backup.json')
LOG_CONFIG_FILE_PATH_FMT = 'configs/log_config{}.json'
MIN_MEMBER_COUNT = 10

LAST_DAYS_ON_PAGE = 2
LAST_DAYS_IN_DB = 30

KEYBOARD_COLUMN_COUNT = 4

MAX_YT_CHANNEL_COUNT = 10
MAX_TAG_COUNT = 40
MAX_TG_COUNT = 10


@dataclass
class Profile:
    token: str = None  # FIXME: Add checking for 'run' command
    work_dir: Path = Path('user_data')
    owner_id: int = 1361728070


@dataclass
class Settings:
    update_interval: float = 30 * 60
    request_delay: float = 1
    send_delay: float = 5 * 60
    error_delay: float = 65
    message_delay: float = 1
    attempt_count: int = 3
    without_sending: bool = False
