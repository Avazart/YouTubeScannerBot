from app.auxiliary_utils import batched_evenly


def test_batched_evenly():
    assert tuple(batched_evenly("123456", 3)) == ("123", "456")
    assert tuple(batched_evenly("1234567", 3)) == ("123", "45", "67")
    assert tuple(batched_evenly("12345678", 3)) == ("123", "456", "78")
