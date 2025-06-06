from typing import TypeAlias

from sqlalchemy import delete, select

from ...bot.bot_types import Status
from ..models import (
    Destination,
    Forwarding,
    TelegramChat,
    TelegramThread,
    YouTubeChannel,
)
from .base import BaseService

TgToYouTubeChannels: TypeAlias = dict[Destination, list[YouTubeChannel]]
TgYtToForwarding: TypeAlias = dict[
    tuple[Destination, YouTubeChannel], Forwarding
]
ForwardingData: TypeAlias = tuple[TgToYouTubeChannels, TgYtToForwarding]


class ForwardingService(BaseService):
    async def add(
        self,
        channel_id: int,
        telegram_chat_id: int,
        telegram_thread_id: int | None,
    ) -> Forwarding:
        f = Forwarding(
            youtube_channel_id=channel_id,
            telegram_chat_id=telegram_chat_id,
            telegram_thread_id=telegram_thread_id,
        )
        await self._s.merge(f)
        return f

    async def remove(
        self,
        channel_id: int,
        telegram_chat_id: int,
        telegram_thread_id: int | None,
    ) -> None:
        q = delete(Forwarding).where(
            (Forwarding.youtube_channel_id == channel_id)
            & (Forwarding.telegram_chat_id == telegram_chat_id)
            & (Forwarding.telegram_thread_id == telegram_thread_id)
        )
        await self._s.execute(q)

    async def get_data(self) -> ForwardingData:
        q = (
            select(TelegramChat, TelegramThread, YouTubeChannel, Forwarding)
            .join(YouTubeChannel)
            .join(TelegramChat)
            .join(
                TelegramThread,
                TelegramThread.id == Forwarding.telegram_thread_id,
                isouter=True,
            )
            .where(TelegramChat.status == int(Status.ON))
            .order_by(Forwarding.youtube_channel_id)
        )
        result = await self._s.execute(q)
        tg_to_youtube_channels: TgToYouTubeChannels = {}
        tg_yt_to_forwarding: TgYtToForwarding = {}
        for row in result.fetchall():
            tg = Destination(chat=row[0], thread=row[1])
            channel, forwarding = row[2], row[3]
            tg_to_youtube_channels.setdefault(tg, []).append(channel)
            tg_yt_to_forwarding[(tg, channel)] = forwarding
        return tg_to_youtube_channels, tg_yt_to_forwarding
