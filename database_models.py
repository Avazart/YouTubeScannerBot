from typing import Any

from sqlalchemy import Column, Integer, DateTime, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base

YOUTUBE_VIDEO_URL_FMT = 'https://www.youtube.com/watch?v={id}'
YOUTUBE_CHANNEL_URL_FMT = 'https://www.youtube.com/channel/{id}/videos'

Base = declarative_base()


def quote_if_str(value: Any):
    return value if type(value) is not str else f'"{value}"'


def to_repr(obj: object) -> str:
    type_name = type(obj).__name__
    values = [f'{name}={quote_if_str(value)}'
              for name, value in obj.__dict__.items()
              if not name.startswith('_') and not callable(value)]
    return f'{type_name}({", ".join(values)})'


class YouTubeChannel(Base):
    __tablename__ = "YouTubeChannels"

    id = Column(String, primary_key=True)
    title = Column(String)
    canonical_base_url = Column(String)
    videos_url = property(lambda self: YOUTUBE_CHANNEL_URL_FMT.format(id=self.id))

    def __repr__(self):
        return to_repr(self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.name == other.name


class TelegramObject(Base):
    __tablename__ = "TelegramObjects"

    id = Column(Integer, primary_key=True)
    type = Column(String, default=None)
    user_name = Column(String, default=None)
    title = Column(String, default=None)
    first_name = Column(String, default=None)
    last_name = Column(String, default=None)
    is_creator = Column(Boolean, default=None)

    def __repr__(self):
        return to_repr(self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == self.id


class Forwarding(Base):
    __tablename__ = "Forwarding"

    n = Column(Integer, primary_key=True, autoincrement=True, default=None)

    youtube_channel_id = Column(ForeignKey("YouTubeChannels.id"), default=None)
    telegram_id = Column(ForeignKey("TelegramObjects.id"), default=None)
    enabled = Column(Boolean, default=True)
    reply_to_message_id = Column(Integer, default=None)
    pattern = Column(String, default=None)

    def __repr__(self):
        return to_repr(self)


class YouTubeVideo(Base):
    __tablename__ = "YouTubeVideo"

    id = Column(String, primary_key=True)
    channel_id = Column(ForeignKey("YouTubeChannels.id"), default=None)

    title = Column(String, default=None)
    style = Column(String, default=None)

    time_ago = Column(String, default=None)
    scan_time = Column(DateTime)
    creation_time = Column(DateTime, default=None)

    url = property(lambda self: YOUTUBE_VIDEO_URL_FMT.format(id=self.id))

    def __repr__(self):
        return to_repr(self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id
