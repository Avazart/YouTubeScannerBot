from sqlalchemy import Table
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Base
from settings import Settings


async def drop_alembic_version_table(connection):
    alembic_table = Table('alembic_version', Base.metadata)
    await connection.run_sync(
        lambda e: alembic_table.drop(e, checkfirst=True)
    )


async def recreate_db(settings: Settings):
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await drop_alembic_version_table(connection)
        await connection.run_sync(Base.metadata.create_all)
