import asyncio
import json
import random
import sys
from logging import getLogger
from logging.config import dictConfig
from pathlib import Path

import click
import colorama
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import click_utils
from backup_utils import export_data, import_channels, import_data
from database.recreate_db import recreate_db
from env_utils import dataclass_from_env
from run import run
from settings import (
    Settings,
    LOG_CONFIG_FILE_PATH_FMT
)


def init_logging(workdir: Path, debug=False):
    logs_path = workdir / 'logs'
    logs_path.mkdir(parents=True, exist_ok=True)
    log_config_path = LOG_CONFIG_FILE_PATH_FMT.format('_debug' if debug else '')
    with open(log_config_path) as file:
        config = json.load(file)
        file_handler = config['handlers']['FileHandler']
        file_handler['filename'] = str(logs_path / 'log.txt')
        dictConfig(config)


@click.group(invoke_without_command=True)
@click.pass_context
def command_group(context):
    settings = dataclass_from_env(Settings)
    if not settings.work_dir.exists():
        settings.work_dir.mkdir()
    init_logging(settings.work_dir, settings.debug)
    context.obj['logger'] = getLogger('main')
    context.obj['settings'] = settings
    if context.invoked_subcommand is None:
        context.invoke(command_run)


@command_group.command(name='run')
@click.pass_context
@click_utils.log_work_process('main')
def command_run(context):
    logger = context.obj['logger']
    settings = context.obj['settings']
    asyncio.run(run(settings, logger))


@command_group.command(name='recreate_db')
@click.pass_context
@click_utils.log_work_process('main')
def command_recreate_db(context):
    settings = context.obj['settings']
    asyncio.run(recreate_db(settings))


@command_group.command(name='import')
@click.argument('file_path', type=click.Path(exists=True), required=True)
@click.pass_context
@click_utils.log_work_process('main')
def command_import(context, file_path: str):
    settings = context.obj['settings']
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    asyncio.run(import_data(Path(file_path), session_maker))


@command_group.command(name='import_channels')
@click.argument('file_path', type=click.Path(exists=True), required=True)
@click.pass_context
@click_utils.log_work_process('main')
def command_import_channels(context, file_path: str):
    settings = context.obj['settings']
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    asyncio.run(import_channels(Path(file_path), session_maker))


@command_group.command(name='export')
@click.argument('file_path', type=click.Path(exists=False), required=True)
@click.pass_context
@click_utils.log_work_process('main')
def command_export(context, file_path: str):
    settings = context.obj['settings']
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    asyncio.run(export_data(Path(file_path), session_maker))


def startup():
    colorama.init()
    random.seed()

    if sys.platform.startswith('win'):
        from win_console_utils import init_win_console

        init_win_console()
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    command_group.main(obj={}, standalone_mode=False)


if __name__ == '__main__':
    startup()
