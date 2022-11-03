import functools
import logging
import sys
from typing import Type, get_type_hints, Iterable, Any

import click


class _Missing:
    pass


_MISSING = _Missing()


class Field:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def _public_not_callable_vars(obj) -> tuple[str, Any]:
    for name, value in vars(obj).items():
        if not name.startswith('_') and not callable(value):
            yield name, value


def _get_class_info(class_: Type) -> dict[str, dict]:
    info = {}
    for name, value in _public_not_callable_vars(class_):
        info[name] = {'default': value}

    for name, type_ in get_type_hints(class_).items():
        if not name.startswith('_'):
            info[name] = dict(type=type_)
            default = getattr(class_, name, _MISSING)
            if default != _MISSING and not callable(default):
                info[name]['default'] = default
    return info


def _make_params(name: str, params: dict) -> tuple[Iterable, dict]:
    default = params.get('default', _MISSING)
    if type(default) is Field:
        f: Field = default
        option_names = f.args or [f'--{name}', ]
        extra_params = params | f.kwargs
        if type_ := f.kwargs.get('type') or params.get('type'):
            extra_params['type'] = type_
        return option_names, extra_params
    else:
        option_names = [f'--{name}', ]
        extra_params = params | dict(required=default is _MISSING)
        if params.get('type') is bool:
            extra_params['is_flag'] = True
        return option_names, extra_params


def option_class(class_: Type):
    def decorator(function):
        for name, params in _get_class_info(class_).items():
            option_names, extra_params = _make_params(name, params)
            function = click.option(*option_names, **extra_params)(function)

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, class_(**kwargs))

        return wrapper

    return decorator


def log_work_process(logger_name: str):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            logger: logging.Logger = logging.getLogger(logger_name)
            try:
                logger.info('Start working ...')
                function(*args, **kwargs)
                logger.info('Work finished.')
            except KeyboardInterrupt:  # Ctrl+C
                logger.warning('Interrupted by user.')
            except BaseException as e:
                logger.exception(f'Error occurred: "{e}"')
                sys.exit(1)
            sys.exit(0)

        return wrapper

    return decorator


if __name__ == '__main__':
    from dataclasses import dataclass


    @dataclass
    class _TestSettings:
        int_var: int
        str_var: str
        int_var2: Field = Field('-iv2', '--int_var2', type=int, default=1)
        int_var3: int = 555


    @click.command()
    @option_class(_TestSettings)
    @click.pass_context
    def _test(context, settings: _TestSettings):
        print(context.obj, settings)


    _storage = {}
    _test.main(obj=_storage, standalone_mode=False)
