import datetime
import zoneinfo

import pytest

from opendate import EST, UTC, DateTime, Time, Timezone, expect_date
from opendate import expect_native_timezone, expect_time
from opendate import expect_utc_timezone, prefer_native_timezone
from opendate import prefer_utc_timezone


def test_timezone_function():
    """Test Timezone function creates proper timezone objects."""
    tz = Timezone('US/Eastern')
    assert isinstance(tz, zoneinfo.ZoneInfo)
    assert tz.key in {'US/Eastern', 'America/New_York'}

    tz_utc = Timezone('UTC')
    assert tz_utc.key == 'UTC'

    tz_gmt = Timezone('GMT')
    assert tz_gmt.key == 'GMT'


def test_expect_time_decorator():
    """Test expect_time decorator converts time-like objects."""
    @expect_time
    def func(t):
        return t

    dt = datetime.time(12, 30, 45)
    result = func(dt)
    assert isinstance(result, Time)
    assert result.hour == 12
    assert result.minute == 30
    assert result.second == 45

    @expect_time
    def func_multiple(t1, t2):
        return (t1, t2)

    t1 = datetime.time(9, 0)
    t2 = datetime.time(17, 0)
    result = func_multiple(t1, t2)
    assert all(isinstance(t, Time) for t in result)


def test_prefer_utc_timezone_decorator():
    """Test prefer_utc_timezone adds UTC timezone when missing."""
    @prefer_utc_timezone
    def get_datetime():
        return DateTime(2022, 1, 1, 12, 0, 0)

    result = get_datetime()
    assert result.tzinfo == UTC

    @prefer_utc_timezone
    def get_datetime_with_tz():
        return DateTime(2022, 1, 1, 12, 0, 0, tzinfo=EST)

    result = get_datetime_with_tz()
    assert result.tzinfo == EST


def test_prefer_native_timezone_decorator():
    """Test prefer_native_timezone adds local timezone when missing."""
    from opendate import LCL

    @prefer_native_timezone
    def get_datetime():
        return DateTime(2022, 1, 1, 12, 0, 0)

    result = get_datetime()
    assert result.tzinfo == LCL

    @prefer_native_timezone
    def get_datetime_with_tz():
        return DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)

    result = get_datetime_with_tz()
    assert result.tzinfo == UTC


def test_expect_utc_timezone_decorator():
    """Test expect_utc_timezone forces UTC timezone."""
    from opendate import LCL

    @expect_utc_timezone
    def get_datetime():
        return DateTime(2022, 1, 1, 12, 0, 0, tzinfo=LCL)

    result = get_datetime()
    assert result.tzinfo == UTC


def test_expect_native_timezone_decorator():
    """Test expect_native_timezone forces local timezone."""
    from opendate import LCL

    @expect_native_timezone
    def get_datetime():
        return DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)

    result = get_datetime()
    assert result.tzinfo == LCL


def test_decorator_handles_none():
    """Test decorators handle None values gracefully."""
    @expect_date
    def func(d):
        return d

    assert func(None) is None

    @prefer_utc_timezone
    def func_tz():
        return None

    assert func_tz() is None


if __name__ == '__main__':
    pytest.main([__file__])
