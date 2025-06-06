from sqlalchemy import delete, desc, distinct, exists, select
from sqlalchemy.sql.functions import count

from ...bot.bot_types import Status
from ..models import (
    Forwarding,
    TelegramChat,
    TelegramThread,
    YouTubeChannel,
    YTChannelCategory,
)
from .base import BaseService


class YTChannelService(BaseService):
    async def get(self, channel_id: int) -> YouTubeChannel | None:
        q = select(YouTubeChannel).where(YouTubeChannel.id == channel_id)
        return await self._s.scalar(q)

    async def get_by_original_id(
        self, original_id: int
    ) -> YouTubeChannel | None:
        q = select(YouTubeChannel).where(
            YouTubeChannel.original_id == original_id
        )
        return await self._s.scalar(q)

    async def remove_by_original_id(self, original_id: str) -> None:
        q = delete(YouTubeChannel).where(
            YouTubeChannel.original_id == original_id
        )
        await self._s.execute(q)

    async def get_all(
        self,
        tg_chat_id: int,
        tg_thread_id: int | None,
        category_ids: set[int],
        offset: int | None,
        limit: int | None,
    ) -> list[tuple[YouTubeChannel, bool]]:
        q = select(
            YouTubeChannel,
            exists(
                select(Forwarding)
                .join(
                    TelegramThread,
                    TelegramThread.id == Forwarding.telegram_thread_id,
                    isouter=True,
                )
                .where(
                    (Forwarding.telegram_chat_id == tg_chat_id)
                    & (TelegramThread.original_id == tg_thread_id)
                    & (Forwarding.youtube_channel_id == YouTubeChannel.id)
                )
            ).label("enabled"),
        )

        if category_ids:
            q = (
                q.join(
                    YTChannelCategory,
                    YTChannelCategory.category_id.in_(category_ids),
                )
                .where(YouTubeChannel.id == YTChannelCategory.channel_id)
                .group_by(YouTubeChannel.id, YTChannelCategory.channel_id)
                .having(
                    count(distinct(YTChannelCategory.category_id))
                    == len(category_ids)
                )
            )
        else:
            q = q.order_by(desc("enabled"))

        if offset is not None:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)

        result = await self._s.execute(q)
        rows = result.fetchall()
        return [(row[0], row[1]) for row in rows]

    async def get_all_active(self) -> list[YouTubeChannel]:
        q = (
            select(YouTubeChannel)
            .join(
                Forwarding, YouTubeChannel.id == Forwarding.youtube_channel_id
            )
            .join(
                TelegramChat,
                TelegramChat.original_id == Forwarding.telegram_chat_id,
            )
            .where(TelegramChat.status == int(Status.ON))
            .distinct()
            .order_by(YouTubeChannel.id)
        )
        result = await self._s.execute(q)
        return result.scalars().all()  # type: ignore
