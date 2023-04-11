import csv
import json
from pathlib import Path

from sqlalchemy.engine import Row
from sqlalchemy.future import select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import Select

from database.models import (
    YouTubeChannel,
    Forwarding,
    Tag,
    YouTubeChannelTag,
    TelegramChat,
    TelegramThread
)
from database.utils import get_tags
from youtube_utils import get_channel_info

MODELS = (YouTubeChannel, TelegramChat, TelegramThread, Forwarding, Tag, YouTubeChannelTag)
TABLES = {getattr(model, '__tablename__'): model for model in MODELS}


def model_object_as_dict(obj) -> dict:
    data = {}
    model_class = type(obj)
    for field_name, field_value in vars(model_class).items():
        if type(field_value) is InstrumentedAttribute:
            data[field_name] = getattr(obj, field_name)
    return data


async def export_data(file_path: Path, session_maker):
    async with session_maker.begin() as session:
        data = {}
        for table_name, table_model in TABLES.items():
            q: Select = select(table_model)
            result = await session.execute(q)
            rows: list[Row] = result.fetchall()
            data[table_name] = [model_object_as_dict(row[0]) for row in rows]
        with file_path.open('w') as file:
            json.dump(data, file, indent=4)


async def import_data(file_path: Path, session_maker):
    with file_path.open('r') as file:
        data = json.load(file)
        for table_name, model in TABLES.items():
            async with session_maker.begin() as session:
                rows = data[table_name]
                records = [model(**row) for row in rows]
                session.add_all(records)


async def import_channels(file_path: Path, session_maker):
    async with session_maker.begin() as session:
        exists_tags = {tag.name: tag for tag in await get_tags(None, None, session)}

    with file_path.open(encoding='utf-8', newline='') as file:
        reader = csv.DictReader(file, delimiter=';')
        for i, row in enumerate(reader):
            url = row['url']
            tags_str = row.get('categories', '') or row.get('tag_names', '')
            print(f'#{i} "{url}" {tags_str}')

            tag_names = set(map(str.strip, tags_str.split(',')))
            new_tag_names = tag_names - set(exists_tags)
            new_tags = [Tag(name=name) for name in new_tag_names]

            if new_tags:
                async with session_maker.begin() as session:
                    session.add_all(new_tags)

            for new_tag in new_tags:
                exists_tags[new_tag.name] = new_tag

            try:
                channel: YouTubeChannel = await get_channel_info(url)
                if channel.canonical_base_url:
                    async with session_maker.begin() as session:
                        await session.merge(channel)

                        for tag_name in tag_names:
                            tag = exists_tags[tag_name]
                            yt_tag = YouTubeChannelTag(tag_id=tag.id, channel_id=channel.id)
                            await session.merge(yt_tag)
            except Exception as e:
                print(f'#{i} "{url}" \n type(e) {e}')
