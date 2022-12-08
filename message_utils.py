import pickle
from asyncio import Queue
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from database.models import Destination, YouTubeVideo, YouTubeChannel
from database.utils import TgToYouTubeChannels
from youtube_utils import ScanData


@dataclass
class ScannerMessage:
    destination: Destination
    youtube_video: YouTubeVideo
    youtube_channel_title: str


MessageGroup = list[ScannerMessage]
MessageGroups = list[MessageGroup]
TgToYouTubeVideos = dict[Destination, list[YouTubeVideo]]


def save_message_queue(file_path: Path, q: Queue[MessageGroup]):
    data = []
    while not q.empty():
        data.append(q.get_nowait())
    with file_path.open('wb') as file:
        pickle.dump(data, file)


def load_message_queue(file_path: Path, last_time:  datetime) -> Queue[MessageGroup]:
    q = Queue()

    def time_filter(m: ScannerMessage) -> bool:
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
    tg_to_yt_videos = {}
    for tg, channels in tg_to_yt_channels.items():
        videos = []
        for channel in channels:
            videos.extend(scan_data.get(channel, []))
        tg_to_yt_videos[tg] = sorted(videos, key=lambda v: v.creation_time)
    return tg_to_yt_videos


def make_message_groups(tg_to_yt_videos: TgToYouTubeVideos,
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
                m = ScannerMessage(tg, videos[i], youtube_channel.title)
                group.append(m)
        groups.append(group)
    return groups
