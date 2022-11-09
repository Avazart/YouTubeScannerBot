from datetime import datetime

import httpx
from dateutil.relativedelta import relativedelta

from database_utils import YouTubeChannel, YouTubeVideo
from youtube_parser import parse_channel_videos, parse_channel_info, parse_time_age

ScanData = dict[YouTubeChannel, list[YouTubeVideo]]


async def get_channel_videos(channel: YouTubeChannel) -> list[YouTubeVideo]:
    params = dict(view=0, sort='dd', flow='grid')
    scan_time = datetime.now()
    async with httpx.AsyncClient() as client:
        headers = {'Accept-Language': 'en-US,en;q=0.5'}
        client.headers.update(headers)
        r = await client.get(channel.videos_url, params=params)
        r.raise_for_status()
        data = parse_channel_videos(r.text)
        videos = []
        for kwargs in data:
            if kwargs['time_ago']:
                time_delta: relativedelta = parse_time_age(kwargs['time_ago'])
                creation_time = scan_time - time_delta
            else:
                creation_time = scan_time
            video = YouTubeVideo(channel_id=channel.id,
                                 scan_time=scan_time,
                                 creation_time=creation_time,
                                 **kwargs)
            videos.append(video)
        return videos


async def get_channel_info(url: str) -> YouTubeChannel:
    params = dict(view=0, sort='dd', flow='grid')
    async with httpx.AsyncClient() as client:
        headers = {'Accept-Language': 'en-US,en;q=0.5'}
        client.headers.update(headers)
        r = await client.get(url, params=params)
        r.raise_for_status()
        return YouTubeChannel(**parse_channel_info(r.text))  # title, id, canonical_base_url

