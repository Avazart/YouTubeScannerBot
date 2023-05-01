import dataclasses
import os
from functools import partial
from pathlib import Path
from typing import (
    Type,
    Any,
    MutableMapping,
    Mapping,
    Iterable,
    TypeAlias,
    Generator,
    get_origin,
    get_args
)

_SIMPLE_TYPES = (bool, int, float, str, Path)
_COLLECTION_TYPES = (list, set, frozenset, tuple, dict)

_ListOrSet = list | set | frozenset
_ListOrSetType: TypeAlias = Type[_ListOrSet]


@dataclasses.dataclass(frozen=True)
class ParseConfig:
    el_sep: str = ';'
    cls_sep: str = '_'
    kv_sep: str = ":"
    strip: bool = False
    skip_empty_parts: bool = False
    upper_case: bool = True


DEFAULT_CONFIG = ParseConfig()


class EnvUtilsException(Exception):
    pass


class VariableRequired(EnvUtilsException):
    def __init__(self, var_name):
        self.var_name = var_name
        super().__init__(f'Variable "{self.var_name}" required!')


class TypeNotSupported(EnvUtilsException):
    def __init__(self, var_name, type_name):
        self.var_name = var_name
        self.type_name = type_name
        super().__init__(f'Variable "{self.var_name}": '
                         f'type "{self.type_name}" not supported!')


class CastValueError(EnvUtilsException):
    def __init__(self, var_name, type_name, value):
        self.var_name = var_name
        self.type_name = type_name
        self.value = value
        super().__init__(f'Variable "{self.var_name}": '
                         f'can`t cast "{self.value}" to {self.type_name}!')


def _split_str(s: str,
               sep: str,
               strip=False,
               skip_empty_parts=False,
               max_split=-1) -> list[str]:
    parts = s.split(sep, max_split) if len(s) != 0 else []
    if strip:
        parts = [str.strip(e) for e in parts]
    if skip_empty_parts:
        parts = [e for e in parts if e]
    return parts


def _str_to_bool(s: str) -> bool:
    """ This function convert string to boolean value """
    sl = s.lower().strip()
    if sl in ('true', 'yes', '1', 'on'):
        return True
    elif sl in ('false', 'no', '0', 'off'):
        return False
    else:
        raise ValueError(f"Could not convert string to bool: '{s}'")


def _parse_simple(value: str, target_type: Type, name: str) -> Any:
    """ Cast string value to 'simple' type """
    try:
        if issubclass(target_type, str):
            return value
        elif issubclass(target_type, bool):
            return _str_to_bool(value)
        else:
            return target_type(value)
    except ValueError:
        raise CastValueError(name, str(target_type), value)


def _parse_list_or_set(value: str,
                       target_type,
                       name: str,
                       config: ParseConfig):
    elements = _split_str(value,
                          config.el_sep,
                          config.strip,
                          config.skip_empty_parts)
    if arg_types := get_args(target_type):
        parse = partial(_parse_simple, target_type=arg_types[0], name=name)
        return target_type(map(parse, elements))
    return target_type(elements)


def _parse_tuple(value: str,
                 target_type,
                 name: str,
                 config: ParseConfig):
    elements = _split_str(value,
                          config.el_sep,
                          config.strip,
                          config.skip_empty_parts)

    if arg_types := get_args(target_type):
        if len(elements) != len(arg_types):
            raise CastValueError(name, str(target_type), value)

        return target_type((
            _parse_simple(element_value, element_type, name)
            for element_value, element_type in zip(elements, arg_types)
        ))

    return target_type(elements)


def _parse_items(s: str,
                 config: ParseConfig) \
        -> Generator[list[str], None, None]:
    parts = _split_str(s,
                       config.el_sep,
                       config.strip,
                       config.skip_empty_parts)
    for s in parts:
        yield _split_str(s,
                         config.kv_sep,
                         config.strip,
                         config.skip_empty_parts,
                         max_split=1)


def _parse_dict(value: str,
                target_type,
                name: str,
                config: ParseConfig) -> MutableMapping:
    items = _parse_items(value, config)
    if arg_types := get_args(target_type):
        kt, vt = arg_types
        return target_type(
            (_parse_simple(k, kt, name), _parse_simple(v, vt, name))
            for k, v in items)
    return target_type(items)


def _from_env(prefix: Iterable[str],
              name: str,
              target_type: Type,
              default: Any,
              env: Mapping,
              config: ParseConfig) -> Any:
    """ Get value from environment and cast value to target_type """

    full_name = config.cls_sep.join((*prefix, name))
    if config.upper_case:
        full_name = full_name.upper()

    value = env.get(full_name, dataclasses.MISSING)
    if value is dataclasses.MISSING:
        if default is dataclasses.MISSING:
            raise VariableRequired(full_name)
        else:
            return default
    elif issubclass(target_type, _SIMPLE_TYPES):
        return _parse_simple(value, target_type, full_name)
    else:
        origin_type = get_origin(target_type) or target_type
        if issubclass(origin_type, tuple):
            return _parse_tuple(value, target_type, full_name, config)
        elif issubclass(origin_type, dict):
            return _parse_dict(value, target_type, full_name, config)
        elif issubclass(origin_type, (list, set, frozenset)):
            return _parse_list_or_set(value, target_type, full_name, config)

    raise TypeNotSupported(full_name, str(target_type))


def _get_default(f: dataclasses.Field) -> Any:
    return f.default \
        if f.default_factory is dataclasses.MISSING \
        else f.default_factory()


def dataclass_from_env(dataclass_type,
                       prefix: str | Iterable[str] | None = None,
                       env: Mapping = os.environ,
                       config: ParseConfig = DEFAULT_CONFIG):
    """ Create dataclass instance with data from os environment """

    if prefix is None:
        prefix = []
    elif isinstance(prefix, str):
        prefix = [prefix, ]

    attrs = {}
    for f in dataclasses.fields(dataclass_type):
        if dataclasses.is_dataclass(f.type):
            attrs[f.name] = dataclass_from_env(f.type, (*prefix, f.name),
                                               env, config)
        else:
            default = _get_default(f)
            attrs[f.name] = _from_env(prefix, f.name, f.type, default,
                                      env, config)
    return dataclass_type(**attrs)
