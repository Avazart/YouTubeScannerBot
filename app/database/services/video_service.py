from sqlalchemy import insert

from ..models import YouTubeVideo
from .base import BaseService


class YTVideoService(BaseService):
    async def insert(self, videos: list[YouTubeVideo]) -> None:
        q = insert(YouTubeVideo).values([v.as_dict() for v in videos])
        q = q.on_conflict_do_nothing(index_elements=["original_id"])
        await self._s.execute(q)
