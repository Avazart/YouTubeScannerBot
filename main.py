import asyncio
import json
import random
import sys
from logging import getLogger, Logger
from logging.config import dictConfig
from pathlib import Path

import click
import colorama
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import click_utils
from backup_utils import import_data, export_data, import_channels
from database.recreate_db import recreate_db
from run import run
from settings import (
    Profile,
    Settings,
    LOG_CONFIG_FILE_PATH_FMT, DB_STRING_FMT, DB_NAME
)


def init_logging(workdir: Path):
    logs_path = workdir / 'logs'
    logs_path.mkdir(parents=True, exist_ok=True)
    log_config_path = LOG_CONFIG_FILE_PATH_FMT.format('_debug' if __debug__ else '')
    with open(log_config_path) as file:
        config = json.load(file)
        file_handler = config['handlers']['FileHandler']
        file_handler['filename'] = str(logs_path / 'log.txt')
        dictConfig(config)


@click.group(invoke_without_command=True)
@click_utils.option_class(Profile)
@click.pass_context
def command_group(context, profile: Profile):
    if not profile.work_dir.exists():
        profile.work_dir.mkdir()
    init_logging(profile.work_dir)
    context.obj['logger'] = getLogger('main')
    context.obj['profile'] = profile
    if context.invoked_subcommand is None:
        context.invoke(command_run)


@command_group.command(name='run')
@click_utils.option_class(Settings)
@click.pass_context
@click_utils.log_work_process('main')
def command_run(context, settings: Settings):
    profile: Profile = context.obj['profile']
    logger: Logger = context.obj['logger']
    asyncio.run(run(profile, settings, logger))


@command_group.command(name='recreate_db')
@click.pass_context
@click_utils.log_work_process('main')
def command_recreate_db(context):
    profile: Profile = context.obj['profile']
    asyncio.run(recreate_db(profile))


@command_group.command(name='import')
@click.argument('file_path', type=click.Path(exists=True), required=True)
@click.pass_context
@click_utils.log_work_process('main')
def command_import(context, file_path: str):
    profile: Profile = context.obj['profile']
    engine = create_async_engine(DB_STRING_FMT.format(profile.work_dir / DB_NAME), echo=False)
    SessionMaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    asyncio.run(import_data(Path(file_path), SessionMaker))


@command_group.command(name='import_channels')
@click.argument('file_path', type=click.Path(exists=True), required=True)
@click.pass_context
@click_utils.log_work_process('main')
def command_import_channels(context, file_path: str):
    profile: Profile = context.obj['profile']
    engine = create_async_engine(DB_STRING_FMT.format(profile.work_dir / DB_NAME), echo=False)
    SessionMaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    asyncio.run(import_channels(Path(file_path), SessionMaker))


@command_group.command(name='export')
@click.argument('file_path', type=click.Path(exists=False), required=True)
@click.pass_context
@click_utils.log_work_process('main')
def command_export(context, file_path: str):
    profile: Profile = context.obj['profile']
    engine = create_async_engine(DB_STRING_FMT.format(profile.work_dir / DB_NAME), echo=False)
    SessionMaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    asyncio.run(export_data(Path(file_path), SessionMaker))


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
