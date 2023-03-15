import os
from dataclasses import dataclass, fields, is_dataclass, MISSING
from functools import partial
from pathlib import Path
from types import GenericAlias
from typing import Type, Any, Mapping, Iterable, get_origin, get_args

_SIMPLE_TYPES = (bool, int, float, str, Path)
_COLLECTION_TYPES = (list, set, frozenset, tuple)


@dataclass(frozen=True)
class ParseConfig:
    el_sep: str = ';'
    cls_sep: str = '_'
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


def _str_to_bool(s: str) -> bool:
    """ This function convert string to boolean value """
    sl = s.lower().strip()
    if sl in ('true', 'yes', '1', 'on'):
        return True
    elif sl in ('false', 'no', '0', 'off'):
        return False
    else:
        raise ValueError(f"Could not convert string to bool: '{s}'")


def _split_string(s: str,
                  sep=';',
                  strip=False,
                  skip_empty_parts=False) -> list[str]:
    parts = s.split(sep) if len(s) != 0 else []
    if strip:
        parts = map(str.strip, parts)
    if skip_empty_parts:
        parts = filter(None, parts)
    return list(parts)


def _cast(value: str, target_type: Type, full_name: str) -> Any:
    """ Cast string value to 'elementary' type """
    try:
        if issubclass(target_type, str):
            return value
        elif issubclass(target_type, bool):
            return _str_to_bool(value)
        else:
            return target_type(value)
    except ValueError:
        raise CastValueError(full_name, str(target_type), value)


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

    value = env.get(full_name, MISSING)
    if value is MISSING:
        if default is MISSING:
            raise VariableRequired(full_name)
        else:
            return default
    elif issubclass(target_type, _SIMPLE_TYPES):
        return _cast(value, target_type, full_name)
    elif issubclass(target_type, _COLLECTION_TYPES):
        return target_type(_split_string(value,
                                         config.el_sep,
                                         config.strip,
                                         config.skip_empty_parts))
    elif type(target_type) is GenericAlias:
        collection_type = get_origin(target_type)
        if issubclass(collection_type, (list, set, frozenset)):
            element_type, *rest = get_args(target_type)
            elements = _split_string(value,
                                     config.el_sep,
                                     config.strip,
                                     config.skip_empty_parts)
            cast = partial(_cast,
                           target_type=element_type,
                           full_name=full_name)
            return collection_type(map(cast, elements))
        elif issubclass(collection_type, tuple):
            element_types = get_args(target_type)
            elements = value.split(config.el_sep)
            if len(elements) != len(element_types):
                raise CastValueError(full_name, str(target_type), value)
            values = []
            for element_value, element_type in zip(elements, element_types):
                values.append(_cast(element_value, element_type, full_name))
            return tuple(values)

    raise TypeNotSupported(full_name, str(target_type))


def dataclass_from_env(dataclass_type,
                       prefix: str | Iterable[str] = None,
                       env: Mapping = os.environ,
                       config: ParseConfig = DEFAULT_CONFIG):
    """ Create dataclass instance with data from os environment """

    if prefix is None:
        prefix = []
    elif isinstance(prefix, str):
        prefix = [prefix, ]

    attrs = {}
    for f in fields(dataclass_type):
        if is_dataclass(f.type):
            attrs[f.name] = dataclass_from_env(f.type, (*prefix, f.name),
                                               env, config)
        else:
            default = f.default \
                if f.default_factory is MISSING \
                else f.default_factory()
            attrs[f.name] = _from_env(prefix, f.name, f.type, default,
                                      env, config)
    return dataclass_type(**attrs)
