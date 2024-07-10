import copy
import pickle
from unittest import mock

import pandas as pd
import pendulum
import pytest
from asserts import assert_equal, assert_not_equal, assert_true
from pendulum.tz import Timezone

from date import NYSE, UTC, Date, DateTime, Time, expect_datetime, now


def test_add():
    """Testing that add function preserves DateTime object
    """
    d = DateTime(2000, 1, 1, 12, 30, tzinfo=UTC)
    assert_equal(d.add(days=1), DateTime(2000, 1, 2, 12, 30, tzinfo=UTC))
    assert_not_equal(d.add(days=1), DateTime(2000, 1, 2, 12, 31, tzinfo=UTC))

    d = DateTime(2000, 1, 1, 12, 30, tzinfo=UTC)
    assert_equal(d.b.add(days=1), DateTime(2000, 1, 3, 12, 30, tzinfo=UTC))
    assert_not_equal(d.b.add(days=1), DateTime(2000, 1, 3, 12, 31, tzinfo=UTC))

    # note that tz is not added if DateTime object and one is not
    # present (like Pendulum)
    d = DateTime(2000, 1, 1, 12, 30)
    assert_equal(d.add(days=1, hours=1, minutes=1), DateTime(2000, 1, 2, 13, 31))


def test_subtract():
    """Testing that subtract function preserves DateTime object
    """
    d = DateTime(2000, 1, 4, 12, 30, tzinfo=UTC)
    assert_equal(d.subtract(days=1), DateTime(2000, 1, 3, 12, 30, tzinfo=UTC))
    assert_not_equal(d.subtract(days=1), DateTime(2000, 1, 3, 12, 31, tzinfo=UTC))

    d = DateTime(2000, 1, 4, 12, 30, tzinfo=UTC)
    assert_equal(d.b.subtract(days=1), DateTime(2000, 1, 3, 12, 30, tzinfo=UTC))
    assert_not_equal(d.b.subtract(days=1), DateTime(2000, 1, 3, 12, 31, tzinfo=UTC))

    # note that tz is not added if DateTime object and one is not
    # present (like Pendulum)
    d = DateTime(2000, 1, 4, 12, 30)
    assert_equal(d.subtract(days=1, hours=1, minutes=1), DateTime(2000, 1, 3, 11, 29))


def test_combine():
    """When combining, ignore default Time parse to UTC"""

    date = Date(2000, 1, 1)
    time = Time.parse('9:30 AM')  # default UTC

    d = DateTime.combine(date, time)
    assert isinstance(d, DateTime)
    assert d._business is False
    assert_equal(d, DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('UTC')))


def test_copy():

    d = pendulum.DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert_equal(copy.copy(d), d)

    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert_equal(copy.copy(d), d)


def test_deepcopy():

    d = pendulum.DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert_equal(copy.deepcopy(d), d)

    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert_equal(copy.deepcopy(d), d)


def test_pickle():

    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)

    with open('datetime.pkl', 'wb') as f:
        pickle.dump(d, f)
    with open('datetime.pkl', 'rb') as f:
        d_ = pickle.load(f)

    assert_equal(d, d_)


def test_now():
    """Managed to create a terrible bug where now returned today()
    """
    assert_not_equal(now(), pendulum.today())
    DateTime.now()  # basic check


@mock.patch('date.DateTime.now')
def test_today(mock):
    mock.return_value = DateTime(2020, 1, 1, 12, 30, tzinfo=UTC)
    D = DateTime.today()
    assert_equal(D, DateTime(2020, 1, 1, 0, 0, tzinfo=UTC))


def test_type():
    """Checking that returned object is of type DateTime,
    not pendulum.DateTime
    """
    d = DateTime.now()
    assert_equal(type(d), DateTime)

    d = DateTime.now(tz=NYSE.tz).entity(NYSE)
    assert_equal(type(d), DateTime)


def test_expects():

    @expect_datetime
    def func(args):
        return args

    p = pendulum.DateTime(2022, 1, 1, tzinfo=UTC)
    d = DateTime(2022, 1, 1, tzinfo=UTC)
    df = pd.DataFrame([['foo', 1], ['bar', 2]], columns=['name', 'value'])

    assert_equal(func(p), d)
    assert_equal(func((p, p)), [d, d])
    assert_equal(func(((p, p), p)), [[d, d], d])
    assert_true(isinstance(func((df, p))[0], pd.DataFrame))


if __name__ == '__main__':
    pytest.main([__file__])
