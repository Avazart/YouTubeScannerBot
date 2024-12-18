from pprint import pprint

import pytest

from app.youtube_utils import get_channel_info


@pytest.mark.parametrize("url", ["https://www.youtube.com/@shopokodu"])
async def test_get_channel_info(url: str):
    info = await get_channel_info(url)
    pprint(info)
