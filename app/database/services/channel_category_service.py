from sqlalchemy import delete, exists, select

from ..models import Category, YTChannelCategory
from .base import BaseService


class YTChannelCategoryService(BaseService):
    async def get_all(
        self,
        channel_id: int,
        offset: int | None,
        limit: int | None,
    ) -> list[tuple[Category, bool]]:
        q = select(
            Category,
            exists(
                select(YTChannelCategory).where(
                    (YTChannelCategory.channel_id == channel_id)
                    & (YTChannelCategory.category_id == Category.id)
                )
            ),
        ).order_by(Category.order)
        if offset is not None:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)
        result = await self._s.execute(q)
        rows = result.fetchall()
        return [(row[0], row[1]) for row in rows]

    async def add(self, channel_id: int, category_id: int) -> None:
        yt_category = YTChannelCategory(
            category_id=category_id,
            channel_id=channel_id,
        )
        await self._s.merge(yt_category)

    async def remove(self, channel_id: int, category_id: int) -> None:
        q = delete(YTChannelCategory).where(
            (YTChannelCategory.category_id == category_id)
            & (YTChannelCategory.channel_id == channel_id)
        )
        await self._s.execute(q)
