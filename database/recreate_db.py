import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Base
from database.utils import create_views
from settings import Settings, VIEWS_SCRIPT_PATH


async def recreate_db(settings: Settings):
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await create_views(VIEWS_SCRIPT_PATH, connection)


def _test():
    settings = Settings(work_dir=Path('../../user_data'),
                        token="",
                        database_url='',
                        bot_admin_ids=frozenset())
    asyncio.run(recreate_db(settings))


if __name__ == "__main__":
    _test()
