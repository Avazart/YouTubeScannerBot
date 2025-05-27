import argparse
import asyncio
import random
import sys
from logging import getLogger
from pathlib import Path

import colorama

from .logging_utils import init_logging
from .run import run
from .settings import Settings

logger = getLogger(Path(__file__).parent.name)


def main() -> int:
    colorama.init()
    random.seed()

    if sys.platform.startswith("win"):
        from .win_console_utils import init_win_console

        init_win_console()
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Path to the environment variables file",
    )
    args = parser.parse_args()
    try:
        settings = Settings(
            _env_file=args.env_file,  # noqa
            _env_nested_delimiter="__",  # noqa
        )  # noqa
        init_logging(settings.log, settings.app_tz)
    except Exception as e:
        print('Error occurred: %s "%s"', type(e), e, file=sys.stderr)
        return 1

    try:
        logger.info("Start work ...")
        asyncio.run(run(settings))
        logger.info("Work finished.")
    except KeyboardInterrupt:  # Ctrl+C
        logger.warning("Interrupted by user.")
    except BaseException as e:
        logger.exception('Error occurred: %s "%s"', type(e), e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
