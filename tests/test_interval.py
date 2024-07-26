
from asserts import assert_equal, assert_not_equal

from date import Date, Interval


def test_range_basic():
    d1, d2 = Date(2001, 1, 1), Date(2001, 12, 31)
    _ = Interval(d1, d2).range()
    assert_equal(_, (d1, d2))


def test_range_business():
    d1, d2 = Date(2001, 1, 1), None
    _ = Interval(d1, d2).range(365)
    assert_equal(_, (d1, Date(2002, 1, 1)))

    d1, d2 = Date(2001, 1, 1), None
    _ = Interval(d1, d2).business().range(365)
    assert_not_equal(_, (d1, Date(2002, 1, 1)))


if __name__ == '__main__':
    __import__('pytest').main([__file__])
