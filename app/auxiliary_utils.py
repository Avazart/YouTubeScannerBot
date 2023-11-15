import math
from typing import Optional, Sequence, Iterator

import aiogram


def get_thread_id(message: aiogram.types.Message) -> Optional[int]:
    return message.message_thread_id if message.is_topic_message else None


def batched_evenly(seq: Sequence, max_batch_size: int) -> Iterator[Sequence]:
    """Batch data evenly with max_batch_size."""

    # batched_evenly('1234567', 3) --> 123 45 67

    total = len(seq)
    batch_count = math.ceil(total / max_batch_size)

    i = 0
    while i < total:
        batch_size = math.ceil((total - i) / batch_count)
        batch = seq[i : i + batch_size]
        yield batch
        i += batch_size
        batch_count -= 1


def split_string(s: str, sep: str, max_split: int = -1) -> list[str]:
    """Split string, strip spaces, skip empty parts"""
    return list(filter(None, map(str.strip, s.split(sep, max_split))))
