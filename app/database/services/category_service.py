from sqlalchemy import delete, select

from ..models import Category
from .base import BaseService


class CategoryService(BaseService):
    async def get_all(
        self,
        offset: int | None,
        limit: int | None,
    ) -> list[Category]:
        q = select(Category).order_by(Category.order)
        if offset is not None:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)
        return list((await self._s.scalars(q)).all())

    async def add(self, category_name: str, category_order: int) -> Category:
        category = Category(name=category_name, order=category_order)
        await self._s.merge(category)
        return category

    async def get_by_name(self, category_name: str) -> Category | None:
        q = select(Category).where(Category.name == category_name)
        return await self._s.scalar(q)

    async def remove_by_name(self, category_name: str) -> None:
        q = delete(Category).where(Category.name == category_name)
        await self._s.execute(q)
