import math
from typing import Optional, Any, Sequence, Generator

import aiogram


def get_thread_id(message: aiogram.types.Message) -> Optional[int]:
    return message.message_thread_id if message.is_topic_message else None


def batched_evenly(seq: Sequence, max_batch_size: int) \
        -> Generator[Sequence, None, None]:
    """ Batch data evenly with max_batch_size."""

    # batched_evenly('1234567', 3) --> 123 45 67

    total = len(seq)
    batch_count = math.ceil(total / max_batch_size)

    i = 0
    while i < total:
        batch_size = math.ceil((total - i) / batch_count)
        batch = seq[i:i + batch_size]
        yield batch
        i += batch_size
        batch_count -= 1


def _quote_if_str(value: Any):
    return value if type(value) is not str else f'"{value}"'


def _vars_ex(obj) -> dict[str, Any]:
    """
         return dict with pairs attribute name - value
         include only 'public' not function attribute
    """
    var_names = vars(obj) if hasattr(obj, '__dict__') else obj.__slots__
    vars_ = {}
    for name in var_names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if not name.startswith('_') and not callable(value):
                vars_[name] = value
    return vars_


def make_repr(obj: object) -> str:
    type_name = type(obj).__name__
    vars_ = _vars_ex(obj)
    values = [f'{name}={_quote_if_str(value)}'
              for name, value in vars_.items()]
    return f'{type_name}({", ".join(values)})'


def split_string(s: str, sep: str, max_split: int = -1) -> list[str]:
    """ Split string, strip spaces, skip empty parts """
    return list(filter(None, map(str.strip, s.split(sep, max_split))))
