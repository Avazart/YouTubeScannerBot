FROM python:3.11

COPY --from=ghcr.io/astral-sh/uv:0.7.3 /uv /uvx /bin/

WORKDIR /youtube_scanner

COPY . /youtube_scanner

RUN uv sync --locked --no-dev