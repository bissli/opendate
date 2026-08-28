import copy
import datetime
import pathlib
import pickle
import zoneinfo
from unittest import mock

import dateutil.tz
import numpy as np
import pandas as pd
import pendulum
import pytest
import pytz
from opendate import EST, UTC, Date, DateTime, Time, expect_datetime
from opendate import get_calendar, now
from pendulum.tz import Timezone


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


def test_negative_days_calendar():
    """Test DateTime add/subtract with negative days in calendar mode."""
    d = DateTime(2024, 4, 1, 12, 30, tzinfo=UTC)
    assert d.add(days=-3) == DateTime(2024, 3, 29, 12, 30, tzinfo=UTC)
    assert d.subtract(days=-3) == DateTime(2024, 4, 4, 12, 30, tzinfo=UTC)

    # year boundary with time preservation
    d2 = DateTime(2024, 1, 1, 8, 0, tzinfo=UTC)
    assert d2.add(days=-1) == DateTime(2023, 12, 31, 8, 0, tzinfo=UTC)


def test_negative_days_business():
    """Test DateTime add/subtract with negative business days and time preservation."""
    d = DateTime(2024, 4, 1, 14, 30, 45, tzinfo=UTC)

    # negative add goes backward, skips Good Friday
    assert d.b.add(days=-1) == DateTime(2024, 3, 28, 14, 30, 45, tzinfo=UTC)
    assert d.b.add(days=-3) == DateTime(2024, 3, 26, 14, 30, 45, tzinfo=UTC)

    # negative subtract goes forward
    assert d.b.subtract(days=-1) == DateTime(2024, 4, 2, 14, 30, 45, tzinfo=UTC)

    # equivalence
    assert d.b.add(days=-5) == d.b.subtract(days=5)
    assert d.b.subtract(days=-3) == d.b.add(days=3)

    # from weekend
    d_sat = DateTime(2024, 3, 30, 9, 0, tzinfo=UTC)
    assert d_sat.b.add(days=-1) == DateTime(2024, 3, 28, 9, 0, tzinfo=UTC)
    assert d_sat.b.add(days=-3) == DateTime(2024, 3, 26, 9, 0, tzinfo=UTC)


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
    """Verify a copy carries the same instant, whoever built the zone.

    pendulum's `__deepcopy__` rebuilds through `self.tz`, which answers
    None for a tzinfo pendulum does not own, so a value carrying a
    driver's zone came back naive. Only opendate's DateTime is fixed:
    the pendulum row below is the shape that already worked.

    Mutation: dropping normalize_timezone from DateTime.__new__, which
        lets a zoneinfo.ZoneInfo reach the instance and makes the copy
        naive.
    Oracle: equality against the source, which is False between an
        aware value and a naive one, plus the -4 hour offset the source
        reports.
    """
    d = pendulum.DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert copy.deepcopy(d) == d

    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert copy.deepcopy(d) == d

    d = DateTime(2026, 8, 28, 8, 1, 27, tzinfo=zoneinfo.ZoneInfo('America/New_York'))
    assert copy.deepcopy(d) == d
    assert copy.deepcopy(d).utcoffset() == datetime.timedelta(hours=-4)


def test_pickle(tmp_path):
    """Test pickle serialization and deserialization of DateTime objects."""
    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)

    pickle_file = tmp_path / 'datetime.pkl'
    with pathlib.Path(pickle_file).open('wb') as f:
        pickle.dump(d, f)
    with pathlib.Path(pickle_file).open('rb') as f:
        d_ = pickle.load(f)

    assert d == d_


def test_now():
    """Managed to create a terrible bug where now returned today()
    """
    assert now() != pendulum.today()
    DateTime.now()  # basic check


@mock.patch('opendate.DateTime.now')
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

    d = DateTime.now(tz=get_calendar('NYSE').tz).calendar('NYSE')
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
    nyse_tz = get_calendar('NYSE').tz
    dt_est = DateTime(2022, 1, 1, 12, 30, 15, tzinfo=nyse_tz)
    t_est = dt_est.time()
    assert t_est.hour == 12
    assert t_est.minute == 30
    assert t_est.second == 15
    assert t_est.tzinfo == nyse_tz

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

    dt = DateTime(2023, 7, 15, 14, 30, 45, tzinfo=get_calendar('NYSE').tz)
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


@pytest.mark.parametrize(('input_str', 'fmt', 'expected'), [
    ('2022-01-15', '%Y-%m-%d', (2022, 1, 15, 0, 0, 0)),
    ('2022-01-15 14:30:45', '%Y-%m-%d %H:%M:%S', (2022, 1, 15, 14, 30, 45)),
    ('15/Jan/2022', '%d/%b/%Y', (2022, 1, 15, 0, 0, 0)),
    ('3:30 PM, Jan 15, 2022', '%I:%M %p, %b %d, %Y', (2022, 1, 15, 15, 30, 0)),
])
def test_datetime_strptime(input_str, fmt, expected):
    """Test the strptime class method parses strings according to format strings."""
    dt = DateTime.strptime(input_str, fmt)
    assert dt.year == expected[0]
    assert dt.month == expected[1]
    assert dt.day == expected[2]
    assert dt.hour == expected[3]
    assert dt.minute == expected[4]
    assert dt.second == expected[5]
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
    """Test replace method preserves DateTime type and calendar."""
    dt = DateTime(2022, 1, 15, 12, 30, 45, tzinfo=UTC).calendar('NYSE')

    result = dt.replace(year=2023)
    assert result == DateTime(2023, 1, 15, 12, 30, 45, tzinfo=UTC)
    assert isinstance(result, DateTime)
    assert result._calendar.name == 'NYSE'

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


def test_datetime_instance_with_pandas_nat():
    """Test DateTime.instance correctly handles pandas NaT (Not-a-Time)."""
    # Test with raise_err=False (default)
    result = DateTime.instance(pd.NaT)
    assert result is None

    # Test with raise_err=True
    with pytest.raises(ValueError, match='Empty value'):
        DateTime.instance(pd.NaT, raise_err=True)


def test_datetime_instance_with_numpy_nat():
    """Test DateTime.instance correctly handles numpy datetime64 NaT."""
    # Test with raise_err=False (default)
    result = DateTime.instance(np.datetime64('NaT'))
    assert result is None

    # Test with raise_err=True
    with pytest.raises(ValueError, match='Empty value'):
        DateTime.instance(np.datetime64('NaT'), raise_err=True)


def test_datetime_instance_with_pandas_timestamp_timezones():
    """Verify a pandas Timestamp's zone arrives as one pendulum reads.

    pandas hands back pytz. The `hasattr(tzinfo, 'zone') or
    hasattr(tzinfo, 'key')` guard this replaces could not tell a
    repaired value from a broken one - a plain zoneinfo.ZoneInfo has
    `key` and passed, and so did the pytz object itself.

    Mutation: dropping normalize_timezone from DateTime.__new__, which
        leaves the pytz DstTzInfo in place - the exact shape that came
        back naive from deepcopy and shifted from subtract.
    Oracle: pendulum's own gate, `.tz`, plus the zone name and the
        January offset of -05:00.
    """
    ts_utc = pd.Timestamp('2022-01-01 12:00:00', tz='UTC')
    dt = DateTime.instance(ts_utc)
    assert dt.tzinfo == UTC

    ts_est = pd.Timestamp('2022-01-01 12:00:00', tz='US/Eastern')
    dt = DateTime.instance(ts_est)

    assert dt.tz is not None
    assert dt.timezone_name in {'US/Eastern', 'America/New_York'}
    assert dt.utcoffset() == datetime.timedelta(hours=-5)
    assert copy.deepcopy(dt).utcoffset() == datetime.timedelta(hours=-5)


def test_datetime_instance_with_numpy_datetime64_various_formats():
    """Test DateTime.instance with various numpy datetime64 formats."""
    # Date only (should add UTC timezone)
    dt1 = DateTime.instance(np.datetime64('2022-01-15'))
    assert dt1.year == 2022
    assert dt1.month == 1
    assert dt1.day == 15
    assert dt1.tzinfo == UTC

    # With time
    dt2 = DateTime.instance(np.datetime64('2022-01-15T14:30:45'))
    assert dt2.hour == 14
    assert dt2.minute == 30
    assert dt2.second == 45

    # Microseconds
    dt3 = DateTime.instance(np.datetime64('2022-01-15T14:30:45.123456'))
    assert dt3.microsecond == 123456


def test_instance_injects_utc_on_naive_datetime():
    """Verify DateTime.instance attaches UTC, not merely something.

    Mutation: attaching the local zone in place of UTC, which the old
        `tzinfo is not None` assertion could not see.
    Oracle: the UTC singleton opendate exports, and a zero offset.
    """
    naive = datetime.datetime(2024, 1, 1, 12, 30, 0)
    assert naive.tzinfo is None

    result = DateTime.instance(naive)

    assert result.tzinfo is UTC
    assert result.utcoffset() == datetime.timedelta(0)


DRIVER_TIMEZONES = [
    zoneinfo.ZoneInfo('America/New_York'),
    datetime.timezone(datetime.timedelta(hours=-4)),
    ]


@pytest.mark.parametrize('tzinfo', DRIVER_TIMEZONES)
@pytest.mark.parametrize('build', [
    lambda tzinfo: DateTime(2026, 8, 28, 8, 1, 27, tzinfo=tzinfo),
    lambda tzinfo: DateTime(2026, 8, 28, 8, 1, 27, 0, tzinfo),
    lambda tzinfo: DateTime.instance(
        datetime.datetime(2026, 8, 28, 8, 1, 27, tzinfo=tzinfo)),
    lambda tzinfo: DateTime.combine(
        Date(2026, 8, 28), Time(8, 1, 27), tzinfo=tzinfo),
    ], ids=['keyword', 'positional', 'instance', 'combine'])
def test_every_way_in_answers_tz(build, tzinfo):
    """Verify `.tz` answers however the value was built.

    A database driver hands back a tzinfo pendulum does not own -
    psycopg3 a zoneinfo.ZoneInfo, psycopg2 a fixed datetime.timezone -
    and pendulum answers `.timezone` and `.tz` for its own two classes
    only. Every rebuild keyed on that answer then loses the zone.

    The `instance` and `combine` rows would survive a fix placed in
    `instance` alone - `combine` ends in `DateTime.instance` - so it is
    the keyword and positional rows that pin the choice of `__new__`.

    Mutation: normalizing inside `instance` rather than inside
        `__new__`, which leaves the keyword and positional rows holding
        the driver's own tzinfo.
    Oracle: pendulum's own gate, `.tz`, which is None for exactly the
        tzinfo classes it cannot read, checked against the -4 hour
        offset the source reports.
    """
    value = build(tzinfo)

    assert value.tz is not None
    assert value.utcoffset() == datetime.timedelta(hours=-4)
    assert (value.hour, value.minute, value.second) == (8, 1, 27)


@pytest.mark.parametrize('tzinfo', DRIVER_TIMEZONES)
def test_arithmetic_on_a_driver_timezone_moves_only_the_clock(tzinfo):
    """Verify add and subtract keep the zone and shift by what was asked.

    pendulum normalizes to UTC, does the arithmetic, then reattaches
    `self.tz`. Where that answered None the result came back naive AND
    carrying UTC digits, so subtracting an hour from 08:01-04:00 read
    11:01 rather than 07:01 - a four hour jump forward, dressed as a
    step back.

    Mutation: dropping normalize_timezone from DateTime.__new__.
    Oracle: hand-computed 07:01:27 for an hour before 08:01:27, and
        the same wall clock a day later, both against the -4 hour
        offset the source reports.
    """
    value = DateTime(2026, 8, 28, 8, 1, 27, tzinfo=tzinfo)

    hour_before = value.subtract(hours=1)
    day_after = value.add(days=1)

    assert (hour_before.hour, hour_before.minute) == (7, 1)
    assert hour_before.utcoffset() == datetime.timedelta(hours=-4)
    assert (day_after.day, day_after.hour) == (29, 8)
    assert day_after.utcoffset() == datetime.timedelta(hours=-4)


@pytest.mark.parametrize(('text', 'offset_hours'), [
    ('2026-08-28T08:01:27-04:00', -4),
    ('2026-08-28T08:01:27+00:00', 0),
    ('2026-08-28T08:01:27+05:30', 5.5),
    ])
def test_parse_of_an_offset_string_answers_tz(text, offset_hours):
    """Verify a parsed offset lands on a timezone pendulum owns.

    This needs no database to reach: pendulum's parser attaches a plain
    `datetime.timezone` to any string spelling an offset, `+00:00`
    included, so a csv column of ISO timestamps was enough.

    Mutation: dropping normalize_timezone from `DateTime.__new__`, which
        `parse` does reach, through `cls.instance`; or reading the offset
        as whole hours, which the +05:30 row catches on its own.
    Oracle: pendulum's own gate, `.tz`, against the offset each string
        spells out.
    """
    parsed = DateTime.parse(text)

    assert parsed.tz is not None
    assert parsed.utcoffset() == datetime.timedelta(hours=offset_hours)


def test_a_named_zone_is_rebuilt_by_name_not_by_offset():
    """Verify the rebuild keeps the zone rather than freezing an offset.

    Mutation: settling every unrecognized tzinfo on the fixed offset it
        reports, which pins August's -04:00 onto the instance and makes
        a January value out of it report -04:00 too.
    Oracle: hand-computed - America/New_York is -04:00 in August and
        -05:00 in January, which a fixed -04:00 cannot both be.
    """
    summer = DateTime(2026, 8, 28, 12, 0, tzinfo=zoneinfo.ZoneInfo('America/New_York'))

    winter = summer.subtract(months=7)

    assert summer.utcoffset() == datetime.timedelta(hours=-4)
    assert winter.utcoffset() == datetime.timedelta(hours=-5)
    assert summer.timezone_name == 'America/New_York'


def test_a_zone_naming_nothing_keeps_its_offset_across_a_transition():
    """Verify a fixed offset stays fixed, which is the deliberate half.

    The converse of the rule above. psycopg2 hands back an offset and no
    zone, so there is no daylight-saving rule to follow and an August
    value stays on its August offset when moved into January. Pinning it
    stops a later change from guessing a zone out of an offset.

    Mutation: resolving a fixed datetime.timezone to whichever named
        zone currently matches its offset, which would make the January
        value report -05:00.
    Oracle: hand-computed - the same -04:00 on both sides of the
        November transition, against the -05:00 a named US Eastern zone
        gives for January.
    """
    summer = DateTime(2026, 8, 28, 12, 0,
                      tzinfo=datetime.timezone(datetime.timedelta(hours=-4)))

    winter = summer.subtract(months=7)

    assert summer.utcoffset() == datetime.timedelta(hours=-4)
    assert winter.utcoffset() == datetime.timedelta(hours=-4)


def test_a_pytz_zone_answers_tz():
    """Verify a pytz zone reaches a pendulum one, by name.

    pandas hands back pytz, and `DateTime.instance` is documented to
    take a pd.Timestamp, so this is the likeliest driver shape after the
    two psycopg ones.

    Mutation: dropping the `.zone` half of the name lookup in
        normalize_timezone, which sends a pytz zone to the offset branch
        and freezes one season onto it.
    Oracle: the zone name, plus the -4 hour August offset, checked on a
        hand-built value and on one out of a pandas Timestamp.
    """
    built = DateTime(2026, 8, 28, 8, 1, 27,
                     tzinfo=pytz.timezone('America/New_York'))
    stamped = DateTime.instance(
        pd.Timestamp('2026-08-28 08:01:27', tz='America/New_York'))

    for value in (built, stamped):
        assert value.tz is not None
        assert value.timezone_name == 'America/New_York'
        assert value.utcoffset() == datetime.timedelta(hours=-4)
        assert copy.deepcopy(value).utcoffset() == datetime.timedelta(hours=-4)


@pytest.mark.parametrize('positional', [False, True])
def test_a_dateutil_zone_answers_tz(positional):
    """Verify a zone naming itself nowhere is read at its own instant.

    `dateutil.tz.gettz` answers no key, no zone, and None from
    `utcoffset(None)`, so until the instant under construction was
    passed through it fell out of normalize_timezone unrebuilt - and
    `.utcoffset()` on the result did not return None, it raised.

    Mutation: passing None rather than the instant under construction,
        which sends every dateutil zone back out unrebuilt.
    Oracle: hand-computed -04:00 in August against -05:00 in January,
        read off two values built from the same zone object.
    """
    zone = dateutil.tz.gettz('America/New_York')
    if positional:
        august = DateTime(2026, 8, 28, 8, 1, 27, 0, zone)
        january = DateTime(2026, 1, 15, 8, 1, 27, 0, zone)
    else:
        august = DateTime(2026, 8, 28, 8, 1, 27, tzinfo=zone)
        january = DateTime(2026, 1, 15, 8, 1, 27, tzinfo=zone)

    assert august.tz is not None
    assert august.utcoffset() == datetime.timedelta(hours=-4)
    assert january.utcoffset() == datetime.timedelta(hours=-5)
    assert copy.deepcopy(august).utcoffset() == datetime.timedelta(hours=-4)
    assert august.subtract(hours=1).hour == 7


@pytest.mark.parametrize('code', ['T-3', 'T+2', 'Y-1', 'P+2b', 'M-1'])
def test_parse_resolves_a_dynamic_code_carrying_an_offset(code):
    """Verify an offset date code resolves, rather than being misread.

    The general parser reads the offset digit as a day of month, so
    'T-3' came back as the third of January - silently, and years away
    from the answer. Only the offset forms were wrong; a bare code was
    already handled further down.

    Mutation: calling `_rust_parse_datetime` before testing the string
        against DATEMATCH, which is what let the general parser answer
        first.
    Oracle: `Date.parse` of the same code, which resolves the codes
        correctly and independently of this path.
    """
    parsed = DateTime.parse(code)

    assert parsed is not None
    assert parsed.date() == Date.parse(code)
    assert (parsed.hour, parsed.minute, parsed.second) == (0, 0, 0)


def test_an_unreadable_zone_is_handed_back_rather_than_raising():
    """Verify a zone pendulum cannot represent survives construction.

    Rebuilding a timezone is a repair, so it must never be the step that
    turns a working value into an exception.

    Mutation: dropping the try/except around the rebuild in
        normalize_timezone, which raises InvalidTimezone for a ZoneInfo
        whose key names no zone.
    Oracle: the value constructing at all, plus the -4 hour offset the
        zone file still reports through the untouched tzinfo.
    """
    with open('/usr/share/zoneinfo/America/New_York', 'rb') as handle:
        unnamed = zoneinfo.ZoneInfo.from_file(handle, key='not/a/zone')

    value = DateTime(2026, 8, 28, 8, 1, 27, tzinfo=unnamed)

    assert value.tz is None
    assert value.utcoffset() == datetime.timedelta(hours=-4)


def test_store_calendar_handles_none_return():
    """store_calendar returns None when decorated fn returns None."""
    from opendate.decorators import store_calendar

    @store_calendar
    def returns_none(self):
        return None

    assert returns_none(Date(2024, 1, 1)) is None


if __name__ == '__main__':
    pytest.main([__file__])
