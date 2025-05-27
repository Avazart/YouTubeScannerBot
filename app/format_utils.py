import re
from collections.abc import Iterable
from string import punctuation
from textwrap import shorten

from .database.models import Destination, YouTubeChannel, YouTubeVideo
from .youtube_utils import ScanData

MAX_TITLE_WIDTH = 30
PLACEHOLDER = " ..."
PATTERN = re.compile(rf"[ {re.escape(punctuation)}]+")


def fmt_video(v: YouTubeVideo) -> str:
    text = shorten(v.title, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)
    return f'"{text}" {v.url}'


def fmt_channel(c: YouTubeChannel) -> str:
    text = shorten(c.title, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)
    return f'"{text}" {c.canonical_url}'


def fmt_videos(videos: Iterable[YouTubeVideo], indent: str = "") -> str:
    if not videos:
        return ""
    return indent + f"\n{indent}".join(map(fmt_video, videos))


def fmt_tg(tg: Destination) -> str:
    title = tg.chat.title or tg.chat.first_name
    if tg.thread and tg.thread.title:
        title += "/" + tg.thread.title

    text = shorten(title, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)
    return f'"{text}" {tg.url}'


def fmt_scan_data(data: ScanData):
    lines = []
    for channel, videos in data.items():
        if videos:
            lines.append(fmt_channel(channel))
            lines.append(fmt_videos(videos, indent=" " * 4))
    return "\n".join(lines)


def fmt_pair(video: YouTubeVideo, tg: Destination) -> str:
    title = tg.chat.title or tg.chat.first_name
    if tg.thread and tg.thread.title:
        title += "/" + tg.thread.title
    return f"{video.title} ==> {title}"


def make_video_line(v: YouTubeVideo, channel_titles: dict[str, str]) -> str:
    creation_time_str = v.creation_time.strftime("%H-%M %d.%m.%y")
    return (
        f"<b>{channel_titles[v.channel_id]}</b> "
        f"<a href='{v.url}'>{v.title}</a> "
        f"({creation_time_str})"
    )


def make_message_text(
    videos: Iterable[YouTubeVideo],
    channel_titles: dict[str, str],
) -> str:
    lines = []
    for n, v in enumerate(videos, start=1):
        lines.append(f"{n}. {make_video_line(v, channel_titles)}")
    return "\n".join(lines)
