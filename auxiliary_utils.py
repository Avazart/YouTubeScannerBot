import math
from collections import deque
from typing import Optional, Iterable, Any

import aiogram


def get_thread_id(message: aiogram.types.Message) -> Optional[int]:
    return message.message_thread_id if message.is_topic_message else None


def evenly_batched(it: Iterable, max_count: int):
    q = deque(it)

    element_in_chunk = max_count
    chunk_count = math.ceil(len(q) / element_in_chunk)

    for chunks_left in range(chunk_count, 0, -1):
        element_in_chunk = math.ceil(len(q) / chunks_left)
        chunk = tuple(q.popleft() for _ in range(element_in_chunk))
        yield chunk


def _quote_if_str(value: Any):
    return value if type(value) is not str else f'"{value}"'


def make_repr(obj: object) -> str:
    type_name = type(obj).__name__
    values = [f'{name}={_quote_if_str(value)}'
              for name, value in obj.__dict__.items()
              if not name.startswith('_') and not callable(value)]
    return f'{type_name}({", ".join(values)})'


def split_string(s: str, sep: str, max_split: int = -1) -> list[str]:
    return list(filter(None, map(str.strip, s.split(sep, max_split))))
