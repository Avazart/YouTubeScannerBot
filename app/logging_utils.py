import json
import logging
from datetime import datetime, tzinfo
from logging.config import dictConfig
from pathlib import Path

from pydantic import BaseModel


class LogSettings(BaseModel):
    dir: Path
    config: Path


def init_logging(log: LogSettings, tz: tzinfo | None = None) -> None:
    log.dir.mkdir(parents=True, exist_ok=True)
    with open(log.config, encoding="utf-8") as file:
        config = json.load(file)
        file_handler = config["handlers"]["FileHandler"]
        file_handler["filename"] = str(log.dir / "log.txt")
        dictConfig(config)

    if tz:
        logging.Formatter.converter = lambda *args: datetime.now(
            tz
        ).timetuple()
