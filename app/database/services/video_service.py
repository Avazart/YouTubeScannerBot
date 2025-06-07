from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import joinedload

from ..models import YouTubeVideo
from .base import BaseService


class YTVideoService(BaseService):
    async def insert(self, videos: list[YouTubeVideo]) -> None:
        q = insert(YouTubeVideo).values([v.as_dict() for v in videos])
        q = q.on_conflict_do_nothing(index_elements=["original_id"])
        await self._s.execute(q)

    async def search(
        self,
        text: str,
        limit: int | None = None,
    ) -> list[YouTubeVideo]:
        stmt = (
            select(YouTubeVideo)
            .options(joinedload(YouTubeVideo.channel))
            .where(YouTubeVideo.title.ilike(f"%{text}%"))
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._s.execute(stmt)
        return result.scalars().all()  # type: ignore
