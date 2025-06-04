import json
import logging
import types
from collections.abc import Callable, Iterator
from datetime import datetime, tzinfo
from functools import wraps
from logging.config import dictConfig
from pathlib import Path

from aiogram import Router
from aiogram.dispatcher.event.telegram import TelegramEventObserver
from aiogram.fsm.scene import HandlerContainer
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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


def _get_function_info(function: Callable) -> str | None:
    if isinstance(function, types.FunctionType):
        name = function.__name__
        file = function.__globals__.get("__file__")
        line = function.__code__.co_firstlineno
        return f'{name} File "{file}", line {line}'
    else:
        return None


def log_async_function(function: Callable):
    function_info = _get_function_info(function)

    @wraps(function)
    async def wrapper(*args, **kwargs):
        if function_info:
            logger.debug(function_info)
        return await function(*args, **kwargs)

    return wrapper


def _enum_observers(router: Router) -> Iterator[TelegramEventObserver]:
    for _, value in vars(router).items():
        if isinstance(value, TelegramEventObserver):
            yield value


def decorate_router_handlers(router: Router, decorator=log_async_function):
    for observer in _enum_observers(router):
        for handler in observer.handlers:
            handler.callback = decorator(handler.callback)

    for sub_router in router.sub_routers:
        decorate_router_handlers(sub_router, decorator)


def decorate_scene_handlers(scene_cls, decorator=log_async_function):
    for handler_container in scene_cls.__scene_config__.handlers:
        if isinstance(handler_container, HandlerContainer):
            handler_container.handler = decorator(handler_container.handler)
