from collections import deque
from typing import Sequence, Mapping, Callable, Any, TypeAlias,  Generator

KiValueGen: TypeAlias = Generator[tuple[Any, Any], None, None]
Callback = Callable[[list, str | int, Any], tuple[bool, Any]]


class SearchError(Exception):
    pass


class NotFound:
    pass


NOT_FOUND = NotFound()


def get(root: Sequence | Mapping,
        *path: str | int,
        default=NOT_FOUND) -> Any | NotFound:
    for e in path:
        if type(e) is int:
            if isinstance(root, Sequence) and e < len(root):
                root = root[e]
            else:
                return default
        elif type(e) is str:
            if isinstance(root, Mapping) and e in root:
                root = root[e]
            else:
                return default
        else:
            raise SearchError('Wrong path!')
    return root


def _iterate_map_or_seq(obj: Sequence | Mapping) -> KiValueGen:
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            yield key, value
    elif isinstance(obj, Sequence) and not isinstance(obj, str):
        for index, value in enumerate(obj):
            yield index, value
    else:
        raise SearchError('Type not supported!')


def _is_composite_object(obj) -> bool:
    return isinstance(obj, Mapping) or \
           (isinstance(obj, Sequence) and not isinstance(obj, str))


def find_first(root: Sequence | Mapping, callback: Callback) -> Any:
    q: deque[Sequence | Mapping] = deque([([], root), ])
    while q:
        path, obj = q.popleft()
        if _is_composite_object(obj):
            for ki, value in _iterate_map_or_seq(obj):
                matched, result = callback(path, ki, value)
                if matched:
                    return result
                else:
                    if _is_composite_object(value):
                        q.append((path + [ki, ], value))
    raise SearchError('Not found!')


def find_all(root: Sequence | Mapping, callback: Callback) -> list:
    q: deque[Sequence[Any] | Mapping[Any, Any]] = deque([([], root), ])
    results = []
    while q:
        path, obj = q.popleft()
        if _is_composite_object(obj):
            for ki, value in _iterate_map_or_seq(obj):
                matched, result = callback(path, ki, value)
                if matched:
                    results.append(result)
                else:
                    if _is_composite_object(value):
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
