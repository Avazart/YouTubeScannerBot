from datetime import datetime, timedelta

from sqlalchemy import select

from ..models import Destination, ForwardedVideo, YouTubeChannel, YouTubeVideo
from .base import BaseService


class ForwardedVideoService(BaseService):
    async def add_forwarded(
        self,
        dest: Destination,
        videos: list[YouTubeVideo],
    ) -> None:
        f_videos = [
            ForwardedVideo(
                video_id=video.id,
                chat_original_id=dest.chat.original_id,
                thread_id=dest.get_thread_id(),
            )
            for video in videos
        ]
        self._s.add_all(f_videos)

    async def get_not_forwarded(
        self,
        dest: Destination,
        channels: list[YouTubeChannel],
        last_days: int | None = None,
        limit: int = 5,
    ) -> list[YouTubeVideo]:
        channel_ids = (ch.id for ch in channels)

        forwarded_subquery = select(ForwardedVideo.video_id).where(
            (ForwardedVideo.chat_original_id == dest.chat.original_id)
            & (ForwardedVideo.thread_id == dest.get_thread_id())
        )

        q = select(YouTubeVideo).filter(
            YouTubeVideo.channel_id.in_(channel_ids)
            & (~YouTubeVideo.id.in_(forwarded_subquery))
        )
        if last_days:
            last_time = datetime.today() - timedelta(days=last_days)
            q = q.where(YouTubeVideo.creation_time >= last_time)

        q = q.order_by(YouTubeVideo.creation_time.desc()).limit(limit)

        result = await self._s.execute(q)
        return result.scalars().all()  # type: ignore
