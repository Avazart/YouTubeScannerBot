import asyncio
import json
import random
import sys
from logging import getLogger
from logging.config import dictConfig
from pathlib import Path

import colorama
from dotenv import load_dotenv

from .settings import Settings
from .run import run


def init_logging(log_dir: Path, mode: str) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_config_path = Path(f"log_configs/{mode}.json")
    with open(log_config_path) as file:
        config = json.load(file)
        file_handler = config["handlers"]["FileHandler"]
        file_handler["filename"] = str(log_dir / "log.txt")
        dictConfig(config)


def main() -> int:
    colorama.init()
    random.seed()

    if sys.platform.startswith("win"):
        from .win_console_utils import init_win_console

        init_win_console()
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if len(sys.argv) == 2:
        env_file = f".env.{sys.argv[1]}"
        load_dotenv(env_file)
    else:
        load_dotenv()

    settings = Settings()
    init_logging(settings.log_dir, settings.mode)
    logger = getLogger(Path(__file__).parent.name)
    try:
        logger.info("Start work ...")
        asyncio.run(run(settings))
        logger.info("Work finished.")
    except KeyboardInterrupt:  # Ctrl+C
        logger.warning("Interrupted by user.")
    except BaseException as e:
        logger.exception(f'Error occurred: "{e}"')
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
