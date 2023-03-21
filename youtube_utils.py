import dataclasses
import itertools
from dataclasses import dataclass
from datetime import datetime
from functools import partial

import aiohttp

from dateutil.relativedelta import relativedelta

from database.utils import YouTubeChannel, YouTubeVideo
from youtube_parser.youtube_parser import parse_channel_info, parse_channel, parse_time_age


@dataclass
class YouTubeChannelData:
    videos: list[YouTubeVideo] = dataclasses.field(default_factory=list)
    streams: list[YouTubeVideo] = dataclasses.field(default_factory=list)
    shorts: list[YouTubeVideo] = dataclasses.field(default_factory=list)

    def __iter__(self):
        return itertools.chain(self.videos, self.streams, self.shorts)

    def __bool__(self):
        return bool(self.videos or self.streams or self.shorts)


ScanData = dict[YouTubeChannel, YouTubeChannelData]


def has_tab(urls: list[str], tab_name: str) -> bool:
    for url in urls:
        if url.endswith(tab_name):
            return True
    return False


def make_video(data: dict, scan_time, channel_id: int) -> YouTubeVideo:
    if data['time_ago']:
        time_delta: relativedelta = parse_time_age(data['time_ago'])
        creation_time = scan_time - time_delta
    else:
        creation_time = scan_time
    return YouTubeVideo(original_id=data['id'],
                        channel_id=channel_id,
                        title=data['title'],
                        style=data['style'],
                        time_ago=data['time_ago'],
                        scan_time=scan_time,
                        creation_time=creation_time,
                        live_24_7=False)


async def get_channel_data(channel: YouTubeChannel) -> YouTubeChannelData:
    scan_time = datetime.now()
    f = partial(make_video, scan_time=scan_time, channel_id=channel.id)

    async with aiohttp.ClientSession() as session:
        headers = {'Accept-Language': 'en-US,en;q=0.5'}
        session.headers.update(headers)

        params = dict(view=0, sort='dd', flow='grid')
        r = await session.get(channel.url + '/videos', params=params)
        r.raise_for_status()
        data = parse_channel(await r.text())

        tab_urls = data['tab_urls']
        videos = list(map(f, data['videos']))
        streams = []
        shorts = []

        for tab_videos, tab_name in zip((streams,), ('/streams',)):
            if has_tab(tab_urls, tab_name):
                r = await session.get(channel.url + tab_name, params=params)
                r.raise_for_status()
                from youtube_parser import search
                try:
                    tab_videos.extend(map(f, parse_channel(await r.text())['videos']))
                except search.SearchError:
                    pass

        return YouTubeChannelData(videos=videos,
                                  streams=streams,
                                  shorts=shorts)


async def get_channel_info(url: str) -> YouTubeChannel:
    params = dict(view=0, sort='dd', flow='grid')
    async with aiohttp.ClientSession() as session:
        headers = {'Accept-Language': 'en-US,en;q=0.5'}
        session.headers.update(headers)
        r = await session.get(url, params=params)
        r.raise_for_status()
        info = parse_channel_info(await r.text())
        return YouTubeChannel(original_id=info['channel_id'],
                              canonical_base_url=info['canonical_base_url'],
                              title=info['title'])
