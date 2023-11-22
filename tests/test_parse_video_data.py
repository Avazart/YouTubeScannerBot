import asyncio
from pathlib import Path
from pprint import pprint

from app.youtube_parser.youtube_parser import parse_channel


async def test_parse_channel_without_streams():
    contents_dir = Path("test_data/channels_without_streams/contents")
    for content_file in contents_dir.glob("*.html"):
        print(f"{content_file.name}")
        with content_file.open("r", encoding="utf-8") as file:
            data = parse_channel(file.read())
            pprint(data, sort_dicts=False)
            assert len(data["videos"]) == 0


if __name__ == "__main__":
    asyncio.run(test_parse_channel_without_streams())
