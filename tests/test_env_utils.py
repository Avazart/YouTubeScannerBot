import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from env_utils import dataclass_from_env, VariableRequired, TypeNotSupported, CastValueError


@pytest.fixture()
def prepare_env():
    data = {
        # simple
        "b": " yes",
        "i": " 10 ",
        "f": " 3.14",
        "s": "test",
        "p": "C:/",

        # list
        "b_list": "0;1;yes; no;on ;off",
        "i_list": "1; 2",
        "s_list": "a; b;c",
        "a_list": "1;a;3.14",
        "empty_list": "",

        # set
        "b_set": "0;1;yes; no;on ;off",
        "i_set": "1; 2",
        "s_set": "a; b;c",
        "a_set": "1;a;3.14",
        "empty_set": "",

        # frozenset
        "b_frozenset": "0;1;yes; no;on ;off",
        "i_frozenset": "1; 2",
        "s_frozenset": "a; b;c",
        "a_frozenset": "1;a;3.14",
        "empty_frozenset": "",

        # tuple
        "v": "ON;2;3.14;text",
        "va": "1;a",

        # dict
        "a_d": 'v1:a;v2:b',
        "i_b_d": " 1:True;2:False",

        # nested
        "v1": "1",
        "b_v2": "2",
        "b_a_v3": "3",
    }
    os.environ.clear()
    os.environ.update(data)


def test_simple_types(prepare_env):
    @dataclass
    class A:
        b: bool
        i: int
        f: float
        s: str
        p: Path

    a1 = dataclass_from_env(A)
    a2 = A(b=True, i=10, f=3.14, s="test", p=Path("C:/"))

    assert a1 == a2


def test_list(prepare_env):
    @dataclass
    class B:
        b_list: list[bool]
        i_list: list[int]
        s_list: list[str]
        a_list: list
        empty_list: list[int]

    b1 = dataclass_from_env(B)
    b2 = B(b_list=[False, True, True, False, True, False],
           i_list=[1, 2],
           s_list=['a', ' b', 'c'],
           a_list=['1', 'a', '3.14'],
           empty_list=[])

    assert b1 == b2


def test_set(prepare_env):
    @dataclass
    class C:
        b_set: set[bool]
        i_set: set[int]
        s_set: set[str]
        a_set: set
        empty_set: set[int]

    c1 = dataclass_from_env(C)
    c2 = C(b_set={False, True, True, False, True, False},
           i_set={1, 2},
           s_set={'a', ' b', 'c'},
           a_set={'1', 'a', '3.14'},
           empty_set=set())

    assert c1 == c2


def test_frozenset(prepare_env):
    @dataclass
    class D:
        b_frozenset: frozenset[bool]
        i_frozenset: frozenset[int]
        s_frozenset: frozenset[str]
        a_frozenset: frozenset
        empty_frozenset: frozenset[int]

    d1 = dataclass_from_env(D)
    d2 = D(b_frozenset=frozenset({False, True, True, False, True, False}),
           i_frozenset=frozenset({1, 2}),
           s_frozenset=frozenset({'a', ' b', 'c'}),
           a_frozenset=frozenset({'1', 'a', '3.14'}),
           empty_frozenset=frozenset())

    assert d1 == d2


def test_tuple(prepare_env):
    @dataclass
    class E:
        v: tuple[bool, int, float, str]
        va: tuple

    e1 = dataclass_from_env(E)
    e2 = E(v=(True, 2, 3.14, 'text'), va=('1', 'a'))

    assert e1 == e2


def test_dict(prepare_env):
    @dataclass
    class D:
        a_d: dict
        i_b_d: dict[int, bool]
    d1 = dataclass_from_env(D)
    d2 = D(a_d={'v1': 'a', 'v2': 'b'},
           i_b_d={1: True, 2: False})

    assert d1 == d2


def test_nested_classes(prepare_env):
    @dataclass
    class A:
        v3: int

    @dataclass
    class B:
        v2: int
        a: A

    @dataclass
    class C:
        b: B
        v1: int

    c1 = dataclass_from_env(C)
    c2 = C(b=B(v2=2, a=A(v3=3)), v1=1)

    assert c1 == c2


def test_exceptions(prepare_env):
    with pytest.raises(VariableRequired):
        @dataclass
        class F:
            not_exist: int

        dataclass_from_env(F)

    class SomeClass:
        pass

    with pytest.raises(TypeNotSupported):
        @dataclass
        class G:
            v: SomeClass

        dataclass_from_env(G)

    with pytest.raises(CastValueError):
        @dataclass
        class J:
            s: float

        dataclass_from_env(J)
