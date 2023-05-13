from dataclasses import dataclass
from typing import Iterable

from .database.models import Destination, YouTubeVideo, YouTubeChannel
from .database.utils import TgToYouTubeChannels, TgYtToForwarding
from .youtube_utils import ScanData


@dataclass
class ScannerMessage:
    destination: Destination
    youtube_video: YouTubeVideo
    youtube_channel_title: str


MessageGroup = list[ScannerMessage]
MessageGroups = list[MessageGroup]
TgToYouTubeVideos = dict[Destination, list[YouTubeVideo]]


def get_tg_to_yt_videos(
        scan_data: ScanData,
        tg_to_yt_channels: TgToYouTubeChannels,
        tg_yt_to_forwarding: TgYtToForwarding
) -> TgToYouTubeVideos:
    tg_to_yt_videos = {}
    for tg, channels in tg_to_yt_channels.items():
        videos: list[YouTubeVideo] = []
        for channel in channels:
            videos.extend(scan_data.get(channel, []))
        tg_to_yt_videos[tg] = sorted(videos, key=lambda v: v.creation_time)
    return tg_to_yt_videos


def make_message_groups(
        tg_to_yt_videos: TgToYouTubeVideos,
        youtube_channels: Iterable[YouTubeChannel]) -> MessageGroups:
    yt_channel_ids = {c.id: c for c in youtube_channels}
    groups: MessageGroups = []
    values = tg_to_yt_videos.values()
    max_count = max((len(videos) for videos in values)) if values else 0
    for i in range(max_count):
        group: MessageGroup = []
        for tg, videos in tg_to_yt_videos.items():
            if i < len(videos):
                youtube_channel = yt_channel_ids[videos[i].channel_id]
                m = ScannerMessage(tg, videos[i], youtube_channel.title)
                group.append(m)
        groups.append(group)
    return groups
