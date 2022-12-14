import json
import re
import bs4
from dateutil.relativedelta import relativedelta

import search

DATA_PATTERN = re.compile(r'\s*var\s+ytInitialData\s*=\s*')
MEASUREMENT_NAMES = frozenset(('second', 'minute', 'hour', 'day', 'week', 'month', 'year'))


class YoutubeParserError(Exception):
    pass


def _parse_init_data(content: str) -> str:
    if m := DATA_PATTERN.search(content):
        start = m.span()[1]
        bracket_counter = 0
        single_quote = False
        double_quote = False
        for i, ch in enumerate(content[start:], start=start):
            if ch == '{' and not any((single_quote, double_quote)):
                bracket_counter += 1
            elif ch == '}' and not any((single_quote, double_quote)):
                bracket_counter -= 1
                if bracket_counter == 0:
                    return content[start:i + 1]
            elif ch == '\"':
                if not single_quote:
                    if i == 0 or content[i - 1] != '\\':
                        double_quote = not double_quote
            elif ch == "'":
                if not double_quote:
                    if i == 0 or content[i - 1] != '\\':
                        single_quote = not single_quote
    raise YoutubeParserError('Variable "ytInitialData" not found!')


def _parse_renderer(video_renderer: dict) -> dict:
    video_id = search.find_first(video_renderer, search.ByKey('videoId'))
    title = search.find_first(video_renderer, search.BySubPath('title', 'runs', 0, 'text'))
    style = search.find_first(video_renderer,
                              search.BySubPath('thumbnailOverlayTimeStatusRenderer', 'style'))
    time_ago = search.get(video_renderer, 'publishedTimeText', 'simpleText', default=None)
    return dict(id=video_id, title=title, style=style, time_ago=time_ago)


def _parse_section_list_renderer(renderer: dict) -> list[dict]:
    videos = []
    items = search.find_first(renderer,
                              search.BySubPath('itemSectionRenderer',
                                               'contents',
                                               0,
                                               'gridRenderer',
                                               'items'))
    for i, item in enumerate(items):
        if video_renderer := item.get('gridVideoRenderer'):
            videos.append(_parse_renderer(video_renderer))
    return videos


def _parse_rich_grid_renderer(renderer: dict) -> list[dict]:
    videos = []
    items = search.find_first(renderer, search.ByKey('contents'))
    for i, item in enumerate(items):
        if item_renderer := item.get('richItemRenderer'):
            video_renderer = search.find_first(item_renderer,
                                               search.BySubPath('content', 'videoRenderer'))
            videos.append(_parse_renderer(video_renderer))
    return videos


def _parse_object(obj_content) -> list[dict]:
    videos = []
    obj = json.loads(obj_content)
    content = search.find_first(obj, search.BySubPath('tabRenderer', 'content'))
    if renderer := content.get('sectionListRenderer'):
        videos.extend(_parse_section_list_renderer(renderer))
    elif renderer := content.get('richGridRenderer'):
        videos.extend(_parse_rich_grid_renderer(renderer))
    else:
        raise YoutubeParserError('Renderer not found!')
    return videos


def parse_channel_videos(content: str) -> list[dict]:
    soup = bs4.BeautifulSoup(content, 'lxml')
    script_els = soup.find_all('script')
    script_with_data_els = list(filter(lambda el: DATA_PATTERN.search(el.text), script_els))
    if len(script_with_data_els) == 0:
        raise YoutubeParserError('"ytInitialData" not found!')
    obj_content = _parse_init_data(script_with_data_els[0].text)
    return _parse_object(obj_content)


def parse_channel_info(content: str) -> dict:
    soup = bs4.BeautifulSoup(content, 'lxml')
    script_els = soup.find_all('script')
    script_with_data_els = list(filter(lambda el: 'ytInitialData' in el.text, script_els))
    if len(script_with_data_els) == 0:
        raise YoutubeParserError('"ytInitialData" not found!')
    obj_content = _parse_init_data(script_with_data_els[0].text)
    obj = json.loads(obj_content)
    tabbed_header_renderer = \
        search.find_first(obj, search.BySubPath('c4TabbedHeaderRenderer',
                                                'channelId',
                                                return_root=True))
    channel_id = tabbed_header_renderer.get('channelId')
    title = tabbed_header_renderer.get('title')
    canonical_base_url = search.get(tabbed_header_renderer,
                                    'navigationEndpoint',
                                    'browseEndpoint',
                                    'canonicalBaseUrl',
                                    default=None)
    return dict(title=title,
                id=channel_id,
                canonical_base_url=canonical_base_url)


def parse_time_age(text: str) -> relativedelta:
    if m := re.search(r'(\d+)\s+(\w+?)s?\s+ago', text):
        value, measurement = int(m.group(1)), m.group(2)
        if measurement not in MEASUREMENT_NAMES:
            raise RuntimeError(f'Measurement "{measurement}" is not supported!')
        return relativedelta(**{measurement + 's': value})
    raise RuntimeError(f'Time "{text}" format is not supported!')
