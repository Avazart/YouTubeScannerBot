from dataclasses import dataclass
from pathlib import Path

DB_NAME = 'database.sqlite'
DB_STRING_FMT = 'sqlite+aiosqlite:///{}'
VIEWS_SCRIPT_PATH = Path('views.sql')
QUEUE_FILE_PATH = Path('queue.pickle')
LOG_CONFIG_FILE_PATH_FMT = 'configs/log_config{}.json'
LAST_VIDEO_COUNT = 30


@dataclass
class Profile:
    api_id: int
    api_hash: str
    name: str = "youtube_scanner"
    workdir: Path = Path('user_data')


@dataclass
class Settings:
    update_interval: float = 20 * 60
    request_delay: float = 1
    send_delay: float = 5 * 60
    error_delay: float = 65
    message_delay: float = 1
    attempt_count: int = 3
    last_days: int = 3
    without_sending: bool = False
