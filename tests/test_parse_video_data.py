from pathlib import Path
from pprint import pprint

import pytest

from app.youtube_parser.youtube_parser import parse_channel

CONTENTS_DIR = Path("tests/test_data/channels_without_streams/contents")


def load_html(file_name: Path) -> str:
    with open(file_name, encoding="utf-8") as file:
        return file.read()


def content_iter():
    contents_dir = Path("tests/test_data/channels_without_streams/contents")
    for content_file in contents_dir.glob("*.html"):
        yield content_file.stem, content_file


@pytest.mark.parametrize("content_file", [CONTENTS_DIR / "shopokodu.html"])
def test_parse_channel_without_streams(content_file: Path):
    print(content_file)
    content = load_html(content_file)
    data = parse_channel(content)
    pprint(data)
