import pickle
from asyncio import Queue
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from database_models import TelegramObject, YouTubeVideo
from youtube_utils import ScanData


@dataclass
class Message:
    telegram_object: TelegramObject
    youtube_video: YouTubeVideo
    youtube_channel_title: str


MessageGroup = list[Message]
MessageGroups = list[MessageGroup]


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


def make_message_groups(data: ScanData,
                        tg_to_yt_channels: Mapping,
                        channel_titles: dict[str,str]) -> MessageGroups:
    tg_to_yt_videos: dict[TelegramObject, list[YouTubeVideo]] = {}
    for tg, yt_channels in tg_to_yt_channels.items():
        videos = []
        for channel in yt_channels:
            videos.extend(data.get(channel, []))
        tg_to_yt_videos[tg] = sorted(videos, key=lambda v: v.creation_time)

    groups: MessageGroups = []
    values = tg_to_yt_videos.values()
    max_count = max((len(videos) for videos in values)) if values else 0
    for i in range(max_count):
        group: MessageGroup = []
        for tg, videos in tg_to_yt_videos.items():
            if i < len(videos):
                m = Message(tg, videos[i], channel_titles[videos[i].channel_id])
                group.append(m)
        groups.append(group)
    return groups
