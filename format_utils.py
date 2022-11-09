from textwrap import shorten
from typing import Iterable

from auxiliary_utils import MessageGroups, Message
from database_models import YouTubeVideo, YouTubeChannel, TelegramObject
from youtube_utils import ScanData

MAX_TITLE_WIDTH = 30
PLACEHOLDER = " ..."


def fmt_video(v: YouTubeVideo) -> str:
    return f'[{v.id}] "{shorten(v.title, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)}"'


def fmt_channel(c: YouTubeChannel) -> str:
    return (f'[{c.id}] '
            f'"{shorten(c.title, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)}" '
            f'https://www.youtube.com{c.canonical_base_url}')


def fmt_videos(videos: Iterable[YouTubeVideo], indent: str = '') -> str:
    if not videos:
        return ''
    return indent + f'\n{indent}'.join(map(fmt_video, videos))


def fmt_tg(tg: TelegramObject) -> str:
    return f'[{tg.id}] ' \
           f'"{shorten(tg.title or tg.first_name, MAX_TITLE_WIDTH, placeholder=PLACEHOLDER)}"'


def fmt_scan_data(data: ScanData):
    lines = []
    for channel, videos in data.items():
        lines.append(fmt_channel(channel))
        if videos:
            lines.append(fmt_videos(videos, indent=" " * 4))
    return '\n'.join(lines)


def fmt_pair(video: YouTubeVideo, tg: TelegramObject) -> str:
    return f'{fmt_video(video)} ==> {fmt_tg(tg)}'


def fmt_groups(groups: MessageGroups, indent: str = '') -> str:
    if not groups:
        return ''
    lines = []
    for n, group in enumerate(groups, 1):
        lines.append(f'Group #{n}')
        for m in group:
            lines.append(f'{indent}{fmt_pair(m.youtube_video, m.telegram_object)}')
    return '\n'.join(lines)


def fmt_message(m: Message, from_name: str) -> str:
    return (f'[{from_name}]: **{m.youtube_channel_title}**\n'
            f'{m.youtube_video.title}\n'
            f'__{m.youtube_video.time_ago if m.youtube_video.time_ago else ""}__\n'
            f'{m.youtube_video.url}')
