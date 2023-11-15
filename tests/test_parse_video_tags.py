import asyncio
import itertools

from app.youtube_utils import get_video_tags


def make_keywords(tags: list[str]) -> frozenset[str]:
    return frozenset(
        map(str.lower, itertools.chain.from_iterable(map(str.split, tags)))
    )


async def test_parse_video_tags():
    expected = [
        "python libraries 2023",
        "best python libraries 2023",
        "best python libraries",
        "best python libraries to learn",
        "top python libraries",
        "python library",
        "python",
        "python libraries",
        "python programming",
        "python libraries explained",
        "python libraries to learn",
        "popular python libraries",
        "python libraries tutorial",
        "python libraries for data analysis",
        "top python libraries 2023",
        "python libraries and their uses",
        "top python libraries to learn",
        "top 10 python libraries",
        "programming libraries python",
    ]
    url = "https://www.youtube.com/watch?v=o06MyVhYte4"
    tags = await get_video_tags(url)
    print(make_keywords(tags))
    assert tags == expected


if __name__ == "__main__":
    asyncio.run(test_parse_video_tags())
