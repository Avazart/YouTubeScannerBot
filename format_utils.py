from textwrap import shorten
from typing import Iterable

from message_utils import ScannerMessage, MessageGroups
from database.models import YouTubeVideo, YouTubeChannel, Destination
from youtube_utils import ScanData

MAX_TITLE_WIDTH = 30
PLACEHOLDER = " ..."


def fmt_video(v: YouTubeVideo) -> str:
    text = shorten(v.title, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)
    return f'"{text}" {v.url}'


def fmt_channel(c: YouTubeChannel) -> str:
    text = shorten(c.title, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)
    return f'"{text}" {c.canonical_url}'


def fmt_videos(videos: Iterable[YouTubeVideo], indent: str = '') -> str:
    if not videos:
        return ''
    return indent + f'\n{indent}'.join(map(fmt_video, videos))


def fmt_tg(tg: Destination) -> str:
    title = tg.chat.title or tg.chat.first_name
    if tg.thread and tg.thread.title:
        title += '/' + tg.thread.title

    text = shorten(title, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)
    return f'"{text}" {tg.url}'


def fmt_scan_data(data: ScanData):
    lines = []
    for channel, videos in data.items():
        if videos:
            lines.append(fmt_channel(channel))
            lines.append(fmt_videos(videos, indent=" " * 4))
    return '\n'.join(lines)


def fmt_pair(video: YouTubeVideo, tg: Destination) -> str:
    title = tg.chat.title or tg.chat.first_name
    if tg.thread and tg.thread.title:
        title += '/' + tg.thread.title
    return f'{video.title} ==> {title}'


def fmt_groups(groups: MessageGroups, indent: str = '') -> str:
    if not groups:
        return ''
    lines = []
    for n, group in enumerate(groups, 1):
        lines.append(f'Group #{n}')
        for m in group:
            lines.append(f'{indent}{fmt_pair(m.youtube_video, m.destination)}')
    return '\n'.join(lines)


def fmt_message(m: ScannerMessage) -> str:
    time_str = m.youtube_video.time_ago if m.youtube_video.time_ago else ""
    return (
        f'<b>{m.youtube_channel_title}</b>\n'
        f'{m.youtube_video.title}\n'
        f'<i>{time_str}</i>\n'
        f'{m.youtube_video.url}'
    )
