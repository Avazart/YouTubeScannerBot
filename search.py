from collections import deque
from typing import Sequence, Mapping, Callable, Any, TypeAlias


class SearchError(Exception):
    pass


class NotFound:
    pass


NOT_FOUND = NotFound()

Callback: TypeAlias = Callable[[list, str | int, Any], tuple[bool, Any]]
SeqOrMap: TypeAlias = Sequence | Mapping


def get(root: SeqOrMap, *path: str | int, default=NOT_FOUND) -> Any | NotFound:
    for e in path:
        if type(e) is int:
            if not isinstance(root, Sequence) or e >= len(root):
                return default
        elif type(e) is str:
            if not isinstance(root, Mapping) or e not in root:
                return default
        else:
            raise SearchError('Wrong path!')
        root = root[e]
    return root


def _iterate_map_or_seq(obj: SeqOrMap) -> tuple[Any, Any]:
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            yield key, value
    elif isinstance(obj, Sequence):
        for index, value in enumerate(obj):
            yield index, value
    else:
        raise SearchError('Type not supported!')


def find_first(root: SeqOrMap, callback: Callback) -> Any:
    q = deque([([], root), ])
    while q:
        path, obj = q.popleft()
        if isinstance(obj, SeqOrMap):
            for ki, value in _iterate_map_or_seq(obj):
                matched, result = callback(path, ki, value)
                if matched:
                    return result
                else:
                    if isinstance(value, SeqOrMap):
                        q.append((path + [ki, ], value))
    raise SearchError('Not found!')


def find_all(root: SeqOrMap, callback: Callback) -> list:
    q = deque([([], root), ])
    results = []
    while q:
        path, obj = q.popleft()
        if isinstance(obj, SeqOrMap):
            for ki, value in _iterate_map_or_seq(obj):
                matched, result = callback(path, ki, value)
                if matched:
                    results.append(result)
                else:
                    if isinstance(value, SeqOrMap):
                        q.append((path + [ki, ], value))
    return results


class ByKey:
    def __init__(self, key: str):
        self._key = key

    def __call__(self, path: list, ki: str | int, value: Any) -> tuple[bool, Any]:
        if (type(ki) is not int) and ki == self._key:
            return True, value
        return False, None  # found, result_value


class BySubPath:
    def __init__(self, *sub_path: str | int, return_root: bool = False):
        self._sub_path = sub_path
        self._return_root = return_root

    def __call__(self, path: list, ki, value: Any) -> tuple[bool, Any]:
        if ki == self._sub_path[0]:
            child_value = get(value, *self._sub_path[1:])
            if child_value is not NOT_FOUND:
                return True, value if self._return_root else child_value
        return False, None
