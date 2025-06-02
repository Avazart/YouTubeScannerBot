import argparse
import asyncio
import random
import sys
from logging import getLogger
from pathlib import Path

import colorama
from pydantic_core import ValidationError

from .logging_utils import init_logging
from .run import run
from .settings import Settings

logger = getLogger(Path(__file__).parent.name)


async def main() -> int:
    colorama.init()
    random.seed()

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
    except ValidationError as e:
        from_ = args.env_file if args.env_file else "system environment"
        error_text = f"Error occurred while loading settings from {from_}\n{e}"
        print(error_text, file=sys.stderr)
        return 1

    init_logging(settings.log, settings.app_tz)
    try:
        logger.info("Start work ...")
        await run(settings)
        logger.info("Work finished.")
    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):  # Ctrl+C
        logger.warning("Interrupted by user.")
    except BaseException as e:  # pylint: disable=broad-exception-caught
        logger.exception('Error occurred: %s "%s"', type(e), e)
        return 1
    return 0


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.exit(asyncio.run(main()))
