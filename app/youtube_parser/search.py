from collections import deque
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any, TypeAlias


class SearchError(Exception):
    pass


class NotFoundType:
    pass


class NotMatchedType:
    pass


KiValueIt: TypeAlias = Iterator[tuple[Any, Any]]
PathItem = str | int  # key for dict or index for list
Callback = Callable[[list, PathItem, Any], Any | NotMatchedType]

NOT_FOUND = NotFoundType()
NOT_MATCHED = NotMatchedType()


def get(
    root: Sequence | Mapping,
    *path: PathItem,
    default: Any | NotFoundType = NOT_FOUND,
) -> Any | NotFoundType:
    for e in path:
        if isinstance(e, int):
            if isinstance(root, Sequence) and e < len(root):
                root = root[e]
            else:
                return default
        elif isinstance(e, str):
            if isinstance(root, Mapping) and e in root:
                root = root[e]
            else:
                return default
        else:
            raise SearchError("Wrong path!")
    return root


def _iterate_map_or_seq(obj: Sequence | Mapping) -> KiValueIt:
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            yield key, value
    elif isinstance(obj, Sequence) and not isinstance(obj, str):
        for index, value in enumerate(obj):
            yield index, value
    else:
        raise SearchError("Type not supported!")


def _is_composite_object(obj) -> bool:
    return isinstance(obj, Mapping) or (
        isinstance(obj, Sequence) and not isinstance(obj, str)
    )


def find_iter(root: Sequence | Mapping, callback: Callback) -> Iterator[Any]:
    q: deque[Sequence[Any] | Mapping[Any, Any]] = deque([([], root)])
    while q:
        path, obj = q.popleft()
        if _is_composite_object(obj):
            for ki, value in _iterate_map_or_seq(obj):
                if (result := callback(path, ki, value)) is not NOT_MATCHED:
                    yield result
                elif _is_composite_object(value):
                    q.append((path + [ki], value))


def find_first(root: Sequence | Mapping, callback: Callback) -> Any:
    if (result := next(find_iter(root, callback), NOT_FOUND)) is NOT_FOUND:
        raise SearchError("Not found!")
    return result


def find_all(root: Sequence | Mapping, callback: Callback) -> list:
    return list(find_iter(root, callback))


class ByKey:
    def __init__(self, key: str):
        self._key = key

    def __call__(
        self, path: list, ki: PathItem, value: Any
    ) -> Any | NotMatchedType:
        if (not isinstance(ki, int)) and ki == self._key:
            return value
        return NOT_MATCHED


class BySubPath:
    def __init__(self, *sub_path: PathItem, return_root: bool = False):
        self._sub_path = sub_path
        self._return_root = return_root

    def __call__(self, path: list, ki, value: Any) -> Any | NotMatchedType:
        if ki == self._sub_path[0]:
            child_value = get(value, *self._sub_path[1:])
            if child_value is not NOT_FOUND:
                return value if self._return_root else child_value
        return NOT_MATCHED
