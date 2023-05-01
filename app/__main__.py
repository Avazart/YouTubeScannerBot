import asyncio
import json
import random
import sys
from logging import getLogger
from logging.config import dictConfig
from pathlib import Path

import colorama

from .env_utils import dataclass_from_env
from .run import run
from app.settings import (
    Settings,
    LOG_CONF_FMT
)


def init_logging(log_dir: Path, debug=False):
    log_dir.mkdir(parents=True, exist_ok=True)
    log_config_path = LOG_CONF_FMT.format('_debug' if debug else '')
    with open(log_config_path) as file:
        config = json.load(file)
        file_handler = config['handlers']['FileHandler']
        file_handler['filename'] = str(log_dir / 'log.txt')
        dictConfig(config)


def main() -> int:
    colorama.init()
    random.seed()

    if sys.platform.startswith('win'):
        from .win_console_utils import init_win_console

        init_win_console()
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    settings = dataclass_from_env(Settings)
    init_logging(settings.log_dir, settings.debug)
    logger = getLogger(Path(__file__).parent.name)
    try:
        logger.info('Start work ...')
        asyncio.run(run(settings, logger))
        logger.info('Work finished.')
    except KeyboardInterrupt:  # Ctrl+C
        logger.warning('Interrupted by user.')
    except BaseException as e:
        logger.exception(f'Error occurred: "{e}"')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
