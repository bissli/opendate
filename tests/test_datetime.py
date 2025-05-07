import copy
import datetime
import pickle
from unittest import mock

import numpy as np
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


def test_business():
    d = DateTime(2024, 11, 4).start_of('day')  # Monday
    assert_equal(d.business().subtract(days=1), DateTime(2024, 11, 1))
    assert_equal(d.subtract(days=1), DateTime(2024, 11, 3))


def test_combine():
    """When combining, ignore default Time parse to UTC"""

    date = Date(2000, 1, 1)
    time = Time.parse('9:30 AM')  # default UTC

    d = DateTime.combine(date, time)
    assert isinstance(d, DateTime)
    assert d._business is False
    assert_equal(d, DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('UTC')))

    # combine with set timezone (from parsed)
    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert_equal(d, DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST')))

    # combine with from instance time
    time = Time.instance(Time(9, 30))
    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert_equal(d, DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST')))

    # combine with from instance time with another timezone
    time = Time.instance(Time(9, 30, tzinfo=Timezone('UTC')))
    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert_equal(d, DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST')))


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


def test_time():
    """Test that time() method correctly extracts time from DateTime while preserving timezone."""
    dt_est = DateTime(2022, 1, 1, 12, 30, 15, tzinfo=NYSE.tz)
    t_est = dt_est.time()
    assert_equal(t_est.hour, 12)
    assert_equal(t_est.minute, 30)
    assert_equal(t_est.second, 15)
    assert_equal(t_est.tzinfo, NYSE.tz)

    dt_utc = DateTime(2022, 1, 1, 12, 30, 15, tzinfo=UTC)
    t_utc = dt_utc.time()
    assert_equal(t_utc.hour, 12)
    assert_equal(t_utc.minute, 30)
    assert_equal(t_utc.second, 15)
    assert_equal(t_utc.tzinfo, UTC)


def test_rfc3339():
    """Test rfc3339 method for ISO 8601 format output."""
    dt = DateTime(2014, 10, 31, 10, 55, 0, tzinfo=UTC)
    assert_equal(dt.rfc3339(), '2014-10-31T10:55:00+00:00')

    dt = DateTime(2023, 7, 15, 14, 30, 45, tzinfo=NYSE.tz)
    assert_equal(dt.rfc3339(), dt.isoformat())


def test_epoch():
    """Test epoch conversion."""
    dt = DateTime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert_equal(dt.epoch(), 0)

    # Test with a specific timestamp
    dt = DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert_equal(dt.epoch(), dt.timestamp())


def test_timestamp_methods():
    """Test fromtimestamp and utcfromtimestamp methods."""
    # Test fromtimestamp
    timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
    dt = DateTime.fromtimestamp(timestamp, UTC)
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 1)
    assert_equal(dt.hour, 0)
    assert_equal(dt.minute, 0)
    assert_equal(dt.second, 0)
    assert_equal(dt.tzinfo, UTC)

    # Test utcfromtimestamp
    dt = DateTime.utcfromtimestamp(timestamp)
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 1)
    assert_equal(dt.hour, 0)
    assert_equal(dt.minute, 0)
    assert_equal(dt.second, 0)
    assert_equal(dt.tzinfo, UTC)


def test_fromordinal():
    """Test fromordinal method."""
    # January 1, 2022 is the 738156th day since January 1, 1
    dt = DateTime.fromordinal(738156)
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 1)
    assert_equal(dt.hour, 0)
    assert_equal(dt.minute, 0)
    assert_equal(dt.second, 0)


def test_parse_with_different_inputs():
    """Test DateTime.parse with various input formats."""
    # Test with date string
    assert_equal(DateTime.parse('2022/1/1').date(), Date(2022, 1, 1))

    # Test with ISO format
    assert_equal(DateTime.parse('2022-01-01T12:30:45Z').hour, 12)
    assert_equal(DateTime.parse('2022-01-01T12:30:45Z').minute, 30)

    # Test with timestamp (integer)
    dt = DateTime.parse(1641038400)  # 2022-01-01 12:00:00 UTC
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 1)

    # Test with special codes
    assert_equal(DateTime.parse('T').date(), Date.today())
    assert_equal(DateTime.parse('Y').date(), Date.today().subtract(days=1))

    # Test with formatted date-time string
    dt = DateTime.parse('Jan 29 2010')
    assert_equal(dt.year, 2010)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 29)

    # Test with date and time parts
    dt = DateTime.parse('Sep 27 17:11')
    assert_equal(dt.month, 9)
    assert_equal(dt.day, 27)
    assert_equal(dt.hour, 17)
    assert_equal(dt.minute, 11)


def test_instance_with_different_types():
    """Test DateTime.instance with various input types."""
    # Test with datetime.date
    dt = DateTime.instance(datetime.date(2022, 1, 1))
    assert_equal(dt.date(), Date(2022, 1, 1))
    assert dt.tzinfo is not None

    # Test with Date object
    dt = DateTime.instance(Date(2022, 1, 1))
    assert_equal(dt.date(), Date(2022, 1, 1))
    assert dt.tzinfo is not None

    # Test with datetime.datetime
    dt = DateTime.instance(datetime.datetime(2022, 1, 1, 12, 30, 15))
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 1)
    assert_equal(dt.hour, 12)
    assert_equal(dt.minute, 30)
    assert_equal(dt.second, 15)
    assert dt.tzinfo is not None

    # Test with Time object
    dt = DateTime.instance(Time(12, 30, 15, tzinfo=UTC))
    assert_equal(dt.hour, 12)
    assert_equal(dt.minute, 30)
    assert_equal(dt.second, 15)
    assert_equal(dt.tzinfo, UTC)

    # Test with pandas Timestamp
    dt = DateTime.instance(pd.Timestamp('2022-01-01 12:30:15'))
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 1)
    assert_equal(dt.hour, 12)
    assert_equal(dt.minute, 30)
    assert_equal(dt.second, 15)

    # Test with numpy datetime64
    dt = DateTime.instance(np.datetime64('2022-01-01T12:30:15'))
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 1)
    assert_equal(dt.hour, 12)
    assert_equal(dt.minute, 30)
    assert_equal(dt.second, 15)


def test_datetime_strptime():
    """Test the strptime class method parses strings according to format strings."""
    # Test basic date format
    dt = DateTime.strptime('2022-01-15', '%Y-%m-%d')
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 15)
    assert_equal(dt.hour, 0)
    assert_equal(dt.minute, 0)
    assert_equal(dt.second, 0)

    # Test with time components
    dt = DateTime.strptime('2022-01-15 14:30:45', '%Y-%m-%d %H:%M:%S')
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 15)
    assert_equal(dt.hour, 14)
    assert_equal(dt.minute, 30)
    assert_equal(dt.second, 45)

    # Test with different format
    dt = DateTime.strptime('15/Jan/2022', '%d/%b/%Y')
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 15)

    # Test with AM/PM
    dt = DateTime.strptime('3:30 PM, Jan 15, 2022', '%I:%M %p, %b %d, %Y')
    assert_equal(dt.year, 2022)
    assert_equal(dt.month, 1)
    assert_equal(dt.day, 15)
    assert_equal(dt.hour, 15)  # 3 PM = 15:00
    assert_equal(dt.minute, 30)

    # Verify result is DateTime instance
    assert isinstance(dt, DateTime)


def test_datetime_utcnow():
    """Test the utcnow class method returns current UTC time."""
    # Get current time for comparison
    import time
    current_timestamp = time.time()

    # Get utcnow result
    dt = DateTime.utcnow()

    # Test that it's a DateTime instance
    assert isinstance(dt, DateTime)

    # Test it has UTC timezone
    assert dt.tzinfo == UTC

    # Test it's close to current time (within 2 seconds to allow for test execution time)
    dt_timestamp = dt.timestamp()
    time_diff = abs(dt_timestamp - current_timestamp)
    assert time_diff < 2


if __name__ == '__main__':
    pytest.main([__file__])
