import pendulum
import pytest
from asserts import assert_equal, assert_not_equal

from date import LCL, UTC, Date, DateTime, Time


def test_time_constructor():
    """None or empty constructor returns current time
    """
    T = Time()
    assert_equal(T, pendulum.Time())
    assert_equal(type(T), Time)


def test_datetime_to_time():

    D = pendulum.DateTime(2022, 1, 1, 12, 30)
    assert_equal(Time.instance(D.time()), Time(12, 30, tzinfo=UTC))


def test_combine():
    """By default, combine return LCL"""

    D = Date(2022, 1, 1)
    T = Time(12, 30)

    _ = DateTime(2022, 1, 1, 12, 30, tzinfo=LCL)
    assert_equal(_.tzinfo, LCL)

    comb = DateTime.combine(D, T, tzinfo=LCL)
    assert_equal(comb, _)

    comb = DateTime.combine(D, T, tzinfo=UTC)
    assert_not_equal(comb, _)

    # ==

    _ = DateTime(2022, 1, 1, 12, 30, tzinfo=LCL)
    assert_equal(_.tzinfo, LCL)

    comb = DateTime.combine(D, T, tzinfo=LCL)
    assert_equal(comb, _)

    comb = DateTime.combine(D, T, tzinfo=UTC)
    assert_not_equal(comb, _)

    # ==

    _ = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert_equal(_.tzinfo, UTC)

    comb = DateTime.combine(D, T, tzinfo=UTC)
    assert_equal(comb, _)

    comb = DateTime.combine(D, T, tzinfo=LCL)
    assert_not_equal(comb, _)


if __name__ == '__main__':
    pytest.main([__file__])
