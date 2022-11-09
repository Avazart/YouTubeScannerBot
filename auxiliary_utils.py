import pickle
from asyncio import Queue
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, Optional, Mapping, Iterable

from database_models import TelegramObject, YouTubeVideo, YouTubeChannel
from database_utils import ForwardingData, TgYtToForwarding, TgToYouTubeChannels
from youtube_utils import ScanData


@dataclass
class Message:
    telegram_object: TelegramObject
    youtube_video: YouTubeVideo
    youtube_channel_title: str
    reply_to_message_id: Optional[int] = None


MessageGroup: TypeAlias = list[Message]
MessageGroups: TypeAlias = list[MessageGroup]
TgToYouTubeVideos: TypeAlias = dict[TelegramObject, list[YouTubeVideo]]


def save_queue(file_path: Path, q: Queue[MessageGroup]):
    data = []
    while not q.empty():
        data.append(q.get_nowait())
    with file_path.open('wb') as file:
        pickle.dump(data, file)


def load_queue(file_path: Path, last_time) -> Queue[MessageGroup]:
    q = Queue()

    def time_filter(m: Message) -> bool:
        return m.youtube_video.creation_time >= last_time

    if file_path.exists():
        with file_path.open('rb') as file:
            data = pickle.load(file)
            for group in data:
                group = list(filter(time_filter, group))
                q.put_nowait(group)
        file_path.unlink()  # remove file
    return q


def get_tg_to_yt_videos(scan_data: ScanData,
                        tg_to_yt_channels: TgToYouTubeChannels) -> TgToYouTubeVideos:
    tg_to_yt_videos: dict[TelegramObject, list[YouTubeVideo]] = {}
    for tg, channels in tg_to_yt_channels.items():
        videos = []
        for channel in channels:
            videos.extend(scan_data.get(channel, []))
        tg_to_yt_videos[tg] = sorted(videos, key=lambda v: v.creation_time)
    return tg_to_yt_videos


def make_message_groups(tg_to_yt_videos: TgToYouTubeVideos,
                        tg_yt_to_forwarding: TgYtToForwarding,
                        youtube_channels: Iterable[YouTubeChannel]) -> MessageGroups:
    youtube_channels = {c.id: c for c in youtube_channels}
    groups: MessageGroups = []
    values = tg_to_yt_videos.values()
    max_count = max((len(videos) for videos in values)) if values else 0
    for i in range(max_count):
        group: MessageGroup = []
        for tg, videos in tg_to_yt_videos.items():
            if i < len(videos):
                youtube_channel = youtube_channels[videos[i].channel_id]
                forwarding = tg_yt_to_forwarding[tg, youtube_channel]
                message_id = forwarding.reply_to_message_id
                m = Message(tg, videos[i], youtube_channel.title, message_id)
                group.append(m)
        groups.append(group)
    return groups
