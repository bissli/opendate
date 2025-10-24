import copy
import datetime
import pickle
from unittest import mock

import numpy as np
import pandas as pd
import pendulum
import pytest
from pendulum.tz import Timezone

from date import EST, NYSE, UTC, Date, DateTime, Time, expect_datetime, now


def test_add():
    """Testing that add function preserves DateTime object
    """
    d = DateTime(2000, 1, 1, 12, 30, tzinfo=UTC)
    assert d.add(days=1) == DateTime(2000, 1, 2, 12, 30, tzinfo=UTC)
    assert d.add(days=1) != DateTime(2000, 1, 2, 12, 31, tzinfo=UTC)

    d = DateTime(2000, 1, 1, 12, 30, tzinfo=UTC)
    assert d.b.add(days=1) == DateTime(2000, 1, 3, 12, 30, tzinfo=UTC)
    assert d.b.add(days=1) != DateTime(2000, 1, 3, 12, 31, tzinfo=UTC)

    # note that tz is not added if DateTime object and one is not
    # present (like Pendulum)
    d = DateTime(2000, 1, 1, 12, 30)
    assert d.add(days=1, hours=1, minutes=1) == DateTime(2000, 1, 2, 13, 31)


def test_subtract():
    """Testing that subtract function preserves DateTime object
    """
    d = DateTime(2000, 1, 4, 12, 30, tzinfo=UTC)
    assert d.subtract(days=1) == DateTime(2000, 1, 3, 12, 30, tzinfo=UTC)
    assert d.subtract(days=1) != DateTime(2000, 1, 3, 12, 31, tzinfo=UTC)

    d = DateTime(2000, 1, 4, 12, 30, tzinfo=UTC)
    assert d.b.subtract(days=1) == DateTime(2000, 1, 3, 12, 30, tzinfo=UTC)
    assert d.b.subtract(days=1) != DateTime(2000, 1, 3, 12, 31, tzinfo=UTC)

    # note that tz is not added if DateTime object and one is not
    # present (like Pendulum)
    d = DateTime(2000, 1, 4, 12, 30)
    assert d.subtract(days=1, hours=1, minutes=1) == DateTime(2000, 1, 3, 11, 29)


def test_business():
    d = DateTime(2024, 11, 4).start_of('day')  # Monday
    assert d.business().subtract(days=1) == DateTime(2024, 11, 1)
    assert d.subtract(days=1) == DateTime(2024, 11, 3)


def test_combine():
    """When combining, ignore default Time parse to UTC"""

    date = Date(2000, 1, 1)
    time = Time.parse('9:30 AM')  # default UTC

    d = DateTime.combine(date, time)
    assert isinstance(d, DateTime)
    assert d._business is False
    assert d == DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('UTC'))

    # combine with set timezone (from parsed)
    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert d == DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST'))

    # combine with from instance time
    time = Time.instance(Time(9, 30))
    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert d == DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST'))

    # combine with from instance time with another timezone
    time = Time.instance(Time(9, 30, tzinfo=Timezone('UTC')))
    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert d == DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST'))


def test_copy():

    d = pendulum.DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert copy.copy(d) == d

    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert copy.copy(d) == d


def test_deepcopy():

    d = pendulum.DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert copy.deepcopy(d) == d

    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert copy.deepcopy(d) == d


def test_pickle(tmp_path):
    """Test pickle serialization and deserialization of DateTime objects."""
    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)

    pickle_file = tmp_path / 'datetime.pkl'
    with open(pickle_file, 'wb') as f:
        pickle.dump(d, f)
    with open(pickle_file, 'rb') as f:
        d_ = pickle.load(f)

    assert d == d_


def test_now():
    """Managed to create a terrible bug where now returned today()
    """
    assert now() != pendulum.today()
    DateTime.now()  # basic check


@mock.patch('date.DateTime.now')
def test_today(mock):
    mock.return_value = DateTime(2020, 1, 1, 12, 30, tzinfo=UTC)
    D = DateTime.today()
    assert D == DateTime(2020, 1, 1, 0, 0, tzinfo=UTC)


def test_type():
    """Checking that returned object is of type DateTime,
    not pendulum.DateTime
    """
    d = DateTime.now()
    assert isinstance(d, DateTime)

    d = DateTime.now(tz=NYSE.tz).entity(NYSE)
    assert isinstance(d, DateTime)


def test_expects():

    @expect_datetime
    def func(args):
        return args

    p = pendulum.DateTime(2022, 1, 1, tzinfo=UTC)
    d = DateTime(2022, 1, 1, tzinfo=UTC)
    df = pd.DataFrame([['foo', 1], ['bar', 2]], columns=['name', 'value'])

    assert func(p) == d
    assert func((p, p)) == [d, d]
    assert func(((p, p), p)) == [[d, d], d]
    assert isinstance(func((df, p))[0], pd.DataFrame)


def test_time():
    """Test that time() method correctly extracts time from DateTime while preserving timezone."""
    dt_est = DateTime(2022, 1, 1, 12, 30, 15, tzinfo=NYSE.tz)
    t_est = dt_est.time()
    assert t_est.hour == 12
    assert t_est.minute == 30
    assert t_est.second == 15
    assert t_est.tzinfo == NYSE.tz

    dt_utc = DateTime(2022, 1, 1, 12, 30, 15, tzinfo=UTC)
    t_utc = dt_utc.time()
    assert t_utc.hour == 12
    assert t_utc.minute == 30
    assert t_utc.second == 15
    assert t_utc.tzinfo == UTC


def test_rfc3339():
    """Test rfc3339 method for ISO 8601 format output."""
    dt = DateTime(2014, 10, 31, 10, 55, 0, tzinfo=UTC)
    assert dt.rfc3339() == '2014-10-31T10:55:00+00:00'

    dt = DateTime(2023, 7, 15, 14, 30, 45, tzinfo=NYSE.tz)
    assert dt.rfc3339() == dt.isoformat()


def test_epoch():
    """Test epoch conversion."""
    dt = DateTime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert dt.epoch() == 0

    # Test with a specific timestamp
    dt = DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert dt.epoch() == dt.timestamp()


def test_timestamp_methods():
    """Test fromtimestamp and utcfromtimestamp methods."""
    # Test fromtimestamp
    timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
    dt = DateTime.fromtimestamp(timestamp, UTC)
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.tzinfo == UTC

    # Test utcfromtimestamp
    dt = DateTime.utcfromtimestamp(timestamp)
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.tzinfo == UTC


def test_fromordinal():
    """Test fromordinal method."""
    # January 1, 2022 is the 738156th day since January 1, 1
    dt = DateTime.fromordinal(738156)
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0


def test_parse_with_different_inputs():
    """Test DateTime.parse with various input formats."""
    # Test with date string
    assert DateTime.parse('2022/1/1').date() == Date(2022, 1, 1)

    # Test with ISO format
    assert DateTime.parse('2022-01-01T12:30:45Z').hour == 12
    assert DateTime.parse('2022-01-01T12:30:45Z').minute == 30

    # Test with timestamp (integer)
    dt = DateTime.parse(1641038400)  # 2022-01-01 12:00:00 UTC
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1

    # Test with special codes
    assert DateTime.parse('T').date() == Date.today()
    assert DateTime.parse('Y').date() == Date.today().subtract(days=1)

    # Test with formatted date-time string
    dt = DateTime.parse('Jan 29 2010')
    assert dt.year == 2010
    assert dt.month == 1
    assert dt.day == 29

    # Test with date and time parts
    dt = DateTime.parse('Sep 27 17:11')
    assert dt.month == 9
    assert dt.day == 27
    assert dt.hour == 17
    assert dt.minute == 11


def test_instance_with_different_types():
    """Test DateTime.instance with various input types."""
    # Test with datetime.date
    dt = DateTime.instance(datetime.date(2022, 1, 1))
    assert dt.date() == Date(2022, 1, 1)
    assert dt.tzinfo is not None

    # Test with Date object
    dt = DateTime.instance(Date(2022, 1, 1))
    assert dt.date() == Date(2022, 1, 1)
    assert dt.tzinfo is not None

    # Test with datetime.datetime
    dt = DateTime.instance(datetime.datetime(2022, 1, 1, 12, 30, 15))
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 15
    assert dt.tzinfo is not None

    # Test with Time object
    dt = DateTime.instance(Time(12, 30, 15, tzinfo=UTC))
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 15
    assert dt.tzinfo == UTC

    # Test with pandas Timestamp
    dt = DateTime.instance(pd.Timestamp('2022-01-01 12:30:15'))
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 15

    # Test with numpy datetime64
    dt = DateTime.instance(np.datetime64('2022-01-01T12:30:15'))
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 15


def test_datetime_strptime():
    """Test the strptime class method parses strings according to format strings."""
    # Test basic date format
    dt = DateTime.strptime('2022-01-15', '%Y-%m-%d')
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 15
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0

    # Test with time components
    dt = DateTime.strptime('2022-01-15 14:30:45', '%Y-%m-%d %H:%M:%S')
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 15
    assert dt.hour == 14
    assert dt.minute == 30
    assert dt.second == 45

    # Test with different format
    dt = DateTime.strptime('15/Jan/2022', '%d/%b/%Y')
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 15

    # Test with AM/PM
    dt = DateTime.strptime('3:30 PM, Jan 15, 2022', '%I:%M %p, %b %d, %Y')
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 15
    assert dt.hour == 15  # 3 PM = 15:00
    assert dt.minute == 30

    # Verify result is DateTime instance
    assert isinstance(dt, DateTime)


def test_datetime_time_extraction():
    """Test extracting time from DateTime with timezone preservation.
    """
    dt_est = DateTime(2022, 1, 1, 12, 30, 15, tzinfo=EST)
    t = dt_est.time()
    assert t.hour == 12
    assert t.minute == 30
    assert t.second == 15
    assert t.tzinfo == EST

    dt_utc = DateTime(2022, 1, 1, 12, 30, 15, tzinfo=UTC)
    t = dt_utc.time()
    assert t.hour == 12
    assert t.minute == 30
    assert t.second == 15
    assert t.tzinfo == UTC


def test_datetime_rfc3339_format():
    """Test RFC 3339 formatting.
    """
    dt = DateTime.parse('Fri, 31 Oct 2014 10:55:00')
    assert dt == DateTime(2014, 10, 31, 10, 55, 0, tzinfo=UTC)
    assert dt.rfc3339() == '2014-10-31T10:55:00+00:00'


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


def test_datetime_astimezone():
    """Test astimezone method for timezone conversion."""
    dt_utc = DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)

    dt_est = dt_utc.astimezone(EST)
    assert dt_est.hour == 7
    assert dt_est.tzinfo == EST
    assert isinstance(dt_est, DateTime)

    dt_utc = DateTime(2022, 6, 1, 12, 0, 0, tzinfo=UTC)
    dt_est = dt_utc.astimezone(EST)
    assert dt_est.hour == 8


def test_datetime_in_timezone():
    """Test in_timezone and in_tz methods for timezone conversion."""
    dt_utc = DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)

    dt_est = dt_utc.in_timezone(EST)
    assert dt_est.hour == 7
    assert dt_est.tzinfo == EST
    assert isinstance(dt_est, DateTime)

    dt_est2 = dt_utc.in_tz(EST)
    assert dt_est2 == dt_est

    dt_utc = DateTime(2022, 6, 1, 12, 0, 0, tzinfo=UTC)
    dt_est = dt_utc.in_timezone(EST)
    assert dt_est.hour == 8


def test_datetime_replace():
    """Test replace method preserves DateTime type and entity."""
    dt = DateTime(2022, 1, 15, 12, 30, 45, tzinfo=UTC).entity(NYSE)

    result = dt.replace(year=2023)
    assert result == DateTime(2023, 1, 15, 12, 30, 45, tzinfo=UTC)
    assert isinstance(result, DateTime)
    assert result._entity == NYSE

    result = dt.replace(month=6)
    assert result == DateTime(2022, 6, 15, 12, 30, 45, tzinfo=UTC)

    result = dt.replace(hour=14)
    assert result == DateTime(2022, 1, 15, 14, 30, 45, tzinfo=UTC)

    result = dt.replace(year=2024, month=12, day=31, hour=23, minute=59, second=59)
    assert result == DateTime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)


def test_datetime_date_extraction():
    """Test date method extracts Date object from DateTime."""
    dt = DateTime(2022, 1, 15, 12, 30, 45, tzinfo=UTC)

    d = dt.date()
    assert d == Date(2022, 1, 15)
    assert isinstance(d, Date)
    assert type(d).__name__ == 'Date'

    dt = DateTime(2023, 12, 31, 23, 59, 59, tzinfo=EST)
    d = dt.date()
    assert d == Date(2023, 12, 31)


if __name__ == '__main__':
    pytest.main([__file__])
