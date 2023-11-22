import asyncio
from pathlib import Path

import aiohttp


async def main():
    channel_list_file = Path("channels_without_streams.txt")
    content_dir = Path("contents")
    with channel_list_file.open("r", encoding="utf-8") as file:
        async with aiohttp.ClientSession() as session:
            headers = {"Accept-Language": "en-US,en;q=0.5"}
            session.headers.update(headers)
            params = dict(view=0, sort="dd", flow="grid")

            for line in file:
                if channel_url := line.strip():
                    print(f"{channel_url=}")
                    r = await session.get(
                        channel_url + "/streams",
                        params=params,
                    )
                    r.raise_for_status()
                    file_name = channel_url.rsplit("/", maxsplit=1)[-1]
                    file_name = file_name.removeprefix("@") + ".html"
                    file_path = content_dir / file_name
                    print(f"{file_path=}")
                    text = await r.text()
                    with file_path.open("w", encoding="utf-8") as content_file:
                        content_file.write(text)


if __name__ == "__main__":
    asyncio.run(main())
