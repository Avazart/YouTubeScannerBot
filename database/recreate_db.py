import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Base
# from database_utils import create_views
from settings import DB_STRING_FMT, Profile, DB_NAME


async def recreate_db(profile: Profile):
    engine = create_async_engine(DB_STRING_FMT.format(profile.work_dir / DB_NAME), echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
        # await create_views(VIEWS_SCRIPT_PATH, connection)


if __name__ == "__main__":
    asyncio.run(recreate_db(Profile(work_dir=Path('../../user_data'))))
