from auxiliary_utils import batched_evenly, make_repr


def test_batched_evenly():
    assert tuple(batched_evenly('123456', 3)) == ('123', '456')
    assert tuple(batched_evenly('1234567', 3)) == ('123', '45', '67')
    assert tuple(batched_evenly('12345678', 3)) == ('123', '456', '78')


def test_make_repr():
    class ClassWithDict:
        def __init__(self):
            self.a = 1
            self.b = 2

    class ClassWithSlots:
        __slots__ = ['a', 'b', 'c']

        def __init__(self):
            self.a = 1
            self.b = 2

    assert make_repr(ClassWithDict()) == "ClassWithDict(a=1, b=2)"
    assert make_repr(ClassWithSlots()) == "ClassWithSlots(a=1, b=2)"
