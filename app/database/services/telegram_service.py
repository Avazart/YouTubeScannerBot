from sqlalchemy import select, update

from ...bot.bot_types import Status
from ..models import Destination, Forwarding, TelegramChat, TelegramThread
from .base import BaseService


class TelegramService(BaseService):
    async def set_status(self, chat_id: int, status: Status) -> None:
        q = (
            update(TelegramChat)
            .values({"status": int(status.next())})
            .where(TelegramChat.original_id == chat_id)
        )
        await self._s.execute(q)

    async def get_all(
        self,
        offset: int | None,
        limit: int | None,
    ) -> list[Destination]:
        q = select(TelegramChat, TelegramThread).join(
            TelegramThread,
            TelegramChat.original_id == TelegramThread.original_chat_id,
            isouter=True,
        )
        if offset is not None:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)
        result = await self._s.execute(q)
        rows = result.fetchall()
        return [Destination(chat=row[0], thread=row[1]) for row in rows]

    async def get_by_user_name(self, user_name: str) -> TelegramChat | None:
        q = select(TelegramChat).where(TelegramChat.user_name == user_name)
        return await self._s.scalar(q)

    async def get(
        self,
        original_chat_id: int,
        original_thread_id: int | None,
    ) -> Destination | None:
        q = (
            select(TelegramChat, TelegramThread)
            .join(
                TelegramThread,
                TelegramChat.original_id == TelegramThread.original_chat_id,
                isouter=True,
            )
            .where(
                (TelegramChat.original_id == original_chat_id)
                & (TelegramThread.original_id == original_thread_id)
            )
        )
        result = await self._s.execute(q)
        if row := result.fetchone():
            return Destination(chat=row[0], thread=row[1])
        return None

    async def get_all_active(self) -> list[Destination]:
        q = (
            select(TelegramChat, TelegramThread)
            .join(
                Forwarding,
                TelegramChat.original_id == Forwarding.telegram_chat_id,
            )
            .outerjoin(
                TelegramThread,
                TelegramThread.id == Forwarding.telegram_thread_id,
            )
            .where(TelegramChat.status == int(Status.ON))
        )
        result = await self._s.execute(q)
        return [
            Destination(chat=row[0], thread=row[1]) for row in result.all()
        ]
