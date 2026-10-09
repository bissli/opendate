import copy
import datetime
import pathlib
import pickle
import time
import zoneinfo
from unittest import mock

import dateutil.tz
import numpy as np
import opendate.constants
import pandas as pd
import pendulum
import pytest
import pytz
from opendate import EST, UTC, Date, DateTime, Time, expect_datetime
from opendate import get_calendar, now
from opendate.decorators import store_calendar
from pendulum.tz import Timezone

NEW_YORK = pendulum.timezone('America/New_York')

PARITY_RECEIVERS = [
    pendulum.DateTime(2024, 11, 3, 5, 30, tzinfo=pendulum.UTC),
    pendulum.DateTime(2024, 11, 3, 6, 30, tzinfo=pendulum.UTC),
    pendulum.DateTime(2024, 3, 10, 7, 30, tzinfo=pendulum.UTC),
    pendulum.DateTime(2024, 11, 3, 1, 30, tzinfo=NEW_YORK, fold=1),
    pendulum.DateTime(2024, 3, 10, 2, 30),
    pendulum.DateTime(2024, 11, 3, 1, 30, fold=1),
    ]

PARITY_TZINFOS = [
    pendulum.UTC,
    NEW_YORK,
    pendulum.timezone('Australia/Sydney'),
    pendulum.fixed_timezone(-18000),
    ]

PARITY_ZONES = [*PARITY_TZINFOS, 'UTC', 'utc', 'Europe/London', 5]


class SummerShiftZone(datetime.tzinfo):
    """-04:00 April through October, else -05:00, and -05:00 for None.
    """

    def utcoffset(self, dt: datetime.datetime | None) -> datetime.timedelta:
        """Offset by month, -05:00 where dt is None.
        """
        summer = dt is not None and 4 <= dt.month <= 10
        return datetime.timedelta(hours=-4 if summer else -5)

    def dst(self, dt: datetime.datetime | None) -> datetime.timedelta:
        """No daylight-saving component.
        """
        return datetime.timedelta(0)

    def tzname(self, dt: datetime.datetime | None) -> str:
        """Fixed label.
        """
        return 'SHIFT'

    def fromutc(self, dt: datetime.datetime) -> datetime.datetime:
        """Dt moved from UTC by the offset of its UTC month.
        """
        return dt + self.utcoffset(dt)


def opendate_twin(value: pendulum.DateTime) -> DateTime:
    """Value's fields, zone and fold as an opendate DateTime.
    """
    return DateTime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=value.tzinfo,
        fold=value.fold)


def parity_key(value: pendulum.DateTime) -> tuple:
    """The parts a caller can see: wall clock and offset, fold, zone name.
    """
    return value.isoformat(), value.fold, value.timezone_name


def test_add():
    """Testing that add function preserves DateTime object

    Mutation: b.add counting calendar days, which lands Saturday
        2000-01-01 plus one business day on Sunday the 2nd.
    Oracle: hand-computed - Monday 2000-01-03 is the next business day.
    """
    d = DateTime(2000, 1, 1, 12, 30, tzinfo=UTC)
    assert d.add(days=1) == DateTime(2000, 1, 2, 12, 30, tzinfo=UTC)
    assert d.add(days=1) != DateTime(2000, 1, 2, 12, 31, tzinfo=UTC)

    d = DateTime(2000, 1, 1, 12, 30, tzinfo=UTC)
    assert d.b.add(days=1) == DateTime(2000, 1, 3, 12, 30, tzinfo=UTC)
    assert d.b.add(days=1) != DateTime(2000, 1, 3, 12, 31, tzinfo=UTC)

    d = DateTime(2000, 1, 1, 12, 30)
    assert d.add(days=1, hours=1, minutes=1) == DateTime(2000, 1, 2, 13, 31)


def test_subtract():
    """Testing that subtract function preserves DateTime object

    Mutation: b.subtract dropping the time of day, or subtract ignoring
        the hours and minutes parts.
    Oracle: hand-computed wall clocks one day, one hour and one minute
        back.
    """
    d = DateTime(2000, 1, 4, 12, 30, tzinfo=UTC)
    assert d.subtract(days=1) == DateTime(2000, 1, 3, 12, 30, tzinfo=UTC)
    assert d.subtract(days=1) != DateTime(2000, 1, 3, 12, 31, tzinfo=UTC)

    d = DateTime(2000, 1, 4, 12, 30, tzinfo=UTC)
    assert d.b.subtract(days=1) == DateTime(2000, 1, 3, 12, 30, tzinfo=UTC)
    assert d.b.subtract(days=1) != DateTime(2000, 1, 3, 12, 31, tzinfo=UTC)

    d = DateTime(2000, 1, 4, 12, 30)
    assert d.subtract(days=1, hours=1, minutes=1) == DateTime(2000, 1, 3, 11, 29)


def test_business():
    """Verify business() makes subtract skip the weekend.

    Mutation: subtract ignoring the business flag, which answers Sunday.
    Oracle: hand-computed - Friday 2024-11-01 precedes Monday 11-04.
    """
    d = DateTime(2024, 11, 4).start_of('day')
    assert d.business().subtract(days=1) == DateTime(2024, 11, 1)
    assert d.subtract(days=1) == DateTime(2024, 11, 3)


def test_negative_days_calendar():
    """Test DateTime add/subtract with negative days in calendar mode.

    Mutation: add or subtract taking the absolute value of days.
    Oracle: hand-computed dates across a month and a year boundary.
    """
    d = DateTime(2024, 4, 1, 12, 30, tzinfo=UTC)
    assert d.add(days=-3) == DateTime(2024, 3, 29, 12, 30, tzinfo=UTC)
    assert d.subtract(days=-3) == DateTime(2024, 4, 4, 12, 30, tzinfo=UTC)

    d2 = DateTime(2024, 1, 1, 8, 0, tzinfo=UTC)
    assert d2.add(days=-1) == DateTime(2023, 12, 31, 8, 0, tzinfo=UTC)


def test_negative_days_business():
    """Test negative business-day add/subtract, keeping the time of day.

    Mutation: the backward business walk skipping weekends only, which
        counts Good Friday as open.
    Oracle: the NYSE calendar - Friday 2024-03-29 is Good Friday, a
        holiday.
    """
    d = DateTime(2024, 4, 1, 14, 30, 45, tzinfo=UTC)

    assert d.b.add(days=-1) == DateTime(2024, 3, 28, 14, 30, 45, tzinfo=UTC)
    assert d.b.add(days=-3) == DateTime(2024, 3, 26, 14, 30, 45, tzinfo=UTC)

    assert d.b.subtract(days=-1) == DateTime(2024, 4, 2, 14, 30, 45, tzinfo=UTC)

    assert d.b.add(days=-5) == d.b.subtract(days=5)
    assert d.b.subtract(days=-3) == d.b.add(days=3)

    d_sat = DateTime(2024, 3, 30, 9, 0, tzinfo=UTC)
    assert d_sat.b.add(days=-1) == DateTime(2024, 3, 28, 9, 0, tzinfo=UTC)
    assert d_sat.b.add(days=-3) == DateTime(2024, 3, 26, 9, 0, tzinfo=UTC)


def test_combine():
    """When combining, ignore default Time parse to UTC

    Mutation: combine converting the time into tzinfo rather than
        setting tzinfo on its wall clock, which moves 9:30 UTC to 4:30.
    Oracle: DateTime built directly at 9:30 in each zone.
    """

    date = Date(2000, 1, 1)
    time = Time.parse('9:30 AM')

    d = DateTime.combine(date, time)
    assert isinstance(d, DateTime)
    assert d._business is False
    assert d == DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('UTC'))

    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert d == DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST'))

    time = Time.instance(Time(9, 30))
    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert d == DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST'))

    time = Time.instance(Time(9, 30, tzinfo=Timezone('UTC')))
    d = DateTime.combine(date, time, tzinfo=Timezone('EST'))
    assert isinstance(d, DateTime)
    assert d._business is False
    assert d == DateTime(2000, 1, 1, 9, 30, 0, tzinfo=Timezone('EST'))


def test_copy():
    """Verify copy.copy keeps the instant and the zone.

    Mutation: an off-by-one tzinfo index in DateTime.__new__ (args[6]
        for args[7]), which breaks the positional form copy rebuilds
        through.
    Oracle: equality against the source.
    """
    d = pendulum.DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert copy.copy(d) == d

    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert copy.copy(d) == d


def test_deepcopy():
    """Verify a copy carries the same instant, whoever built the zone.

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
    """Test pickle serialization and deserialization of DateTime objects.

    Mutation: an off-by-one tzinfo index in DateTime.__new__ (args[6]
        for args[7]), which breaks the positional form unpickling
        rebuilds through.
    Oracle: equality against the source.
    """
    d = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)

    pickle_file = tmp_path / 'datetime.pkl'
    with pathlib.Path(pickle_file).open('wb') as f:
        pickle.dump(d, f)
    with pathlib.Path(pickle_file).open('rb') as f:
        d_ = pickle.load(f)

    assert d == d_


def test_now():
    """Verify now() answers the current time of day.

    Mutation: now() answering the start of the day.
    Oracle: pendulum.today(), which is midnight.
    """
    assert now() != pendulum.today()
    DateTime.now()


@mock.patch('opendate.DateTime.now')
def test_today(mock):
    """Verify today() is the start of the day now() falls on.

    Mutation: today() returning now() without start_of('day').
    Oracle: hand-computed midnight of the mocked 12:30 reading.
    """
    mock.return_value = DateTime(2020, 1, 1, 12, 30, tzinfo=UTC)
    result = DateTime.today()
    assert result == DateTime(2020, 1, 1, 0, 0, tzinfo=UTC)


def test_type():
    """Checking that returned object is of type DateTime,
    not pendulum.DateTime

    Mutation: now() building a pendulum.DateTime rather than cls, or
        calendar() returning the pendulum type.
    Oracle: isinstance against opendate's DateTime.
    """
    d = DateTime.now()
    assert isinstance(d, DateTime)

    d = DateTime.now(tz=get_calendar('NYSE').tz).calendar('NYSE')
    assert isinstance(d, DateTime)


def test_expects():
    """Verify expect_datetime converts nested arguments and skips frames.

    Mutation: expect_datetime passing a tuple through as a tuple rather
        than a list, or converting a DataFrame.
    Oracle: hand-built lists of DateTime, and the DataFrame type.
    """

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


@pytest.mark.parametrize(
    'tzinfo',
    [get_calendar('NYSE').tz, EST, UTC],
    ids=['NYSE', 'EST', 'UTC'])
def test_time(tzinfo):
    """Test that time() extracts the time of day, keeping the timezone.

    Mutation: time() dropping the DateTime's tzinfo, which leaves the
        Time on UTC.
    Oracle: the zone the DateTime was built with.
    """
    t = DateTime(2022, 1, 1, 12, 30, 15, tzinfo=tzinfo).time()
    assert t.hour == 12
    assert t.minute == 30
    assert t.second == 15
    assert t.tzinfo == tzinfo


def test_rfc3339():
    """Test rfc3339 method for ISO 8601 format output.

    Mutation: rfc3339 dropping the offset, or writing Z for UTC.
    Oracle: the hand-written RFC 3339 string.
    """
    dt = DateTime(2014, 10, 31, 10, 55, 0, tzinfo=UTC)
    assert dt.rfc3339() == '2014-10-31T10:55:00+00:00'

    dt = DateTime(2023, 7, 15, 14, 30, 45, tzinfo=get_calendar('NYSE').tz)
    assert dt.rfc3339() == dt.isoformat()


def test_epoch():
    """Test epoch conversion.

    Mutation: epoch reading the wall clock as local time, or answering
        milliseconds.
    Oracle: 0 at the Unix epoch.
    """
    dt = DateTime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert dt.epoch() == 0

    dt = DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert dt.epoch() == dt.timestamp()


def test_timestamp_methods():
    """Test fromtimestamp and utcfromtimestamp methods.

    Mutation: fromtimestamp ignoring tz and reading local time, or
        utcfromtimestamp answering a naive value.
    Oracle: hand-computed - 1640995200 is 2022-01-01 00:00:00 UTC.
    """
    timestamp = 1640995200
    dt = DateTime.fromtimestamp(timestamp, UTC)
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.tzinfo == UTC

    dt = DateTime.utcfromtimestamp(timestamp)
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.tzinfo == UTC


def test_fromordinal():
    """Test fromordinal method.

    Mutation: an off-by-one ordinal, counting from day 0.
    Oracle: hand-computed - 738156 is the ordinal of 2022-01-01.
    """
    dt = DateTime.fromordinal(738156)
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0


def test_parse_with_different_inputs():
    """Test DateTime.parse with various input formats.

    Mutation: parse reading a 10-digit timestamp as milliseconds, or Y
        resolving to today.
    Oracle: hand-computed - 1641038400 is 2022-01-01 12:00:00 UTC.
    """
    assert DateTime.parse('2022/1/1').date() == Date(2022, 1, 1)

    assert DateTime.parse('2022-01-01T12:30:45Z').hour == 12
    assert DateTime.parse('2022-01-01T12:30:45Z').minute == 30

    dt = DateTime.parse(1641038400)
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1

    assert DateTime.parse('T').date() == Date.today()
    assert DateTime.parse('Y').date() == Date.today().subtract(days=1)

    dt = DateTime.parse('Jan 29 2010')
    assert dt.year == 2010
    assert dt.month == 1
    assert dt.day == 29

    dt = DateTime.parse('Sep 27 17:11')
    assert dt.month == 9
    assert dt.day == 27
    assert dt.hour == 17
    assert dt.minute == 11


def test_parse_error_names_the_input():
    """Verify DateTime.parse's ValueError message carries the rejected string.

    Mutation: a logging-style ('...%s', s) pair passed to ValueError,
        which never fills in the placeholder.
    Oracle: the legacy tc to_datetime message
        'Invalid date-time format: ' + s.
    """
    with pytest.raises(ValueError, match='^Invalid date-time format: zzz$'):
        DateTime.parse('zzz', raise_err=True)


def test_instance_with_different_types():
    """Test DateTime.instance with various input types.

    Mutation: instance dropping its date branch, so a datetime.date
        reaches the tzinfo read and raises AttributeError.
    Oracle: the fields each input was built with.
    """
    dt = DateTime.instance(datetime.date(2022, 1, 1))
    assert dt.date() == Date(2022, 1, 1)
    assert dt.tzinfo is not None

    dt = DateTime.instance(Date(2022, 1, 1))
    assert dt.date() == Date(2022, 1, 1)
    assert dt.tzinfo is not None

    dt = DateTime.instance(datetime.datetime(2022, 1, 1, 12, 30, 15))
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 15
    assert dt.tzinfo is not None

    dt = DateTime.instance(Time(12, 30, 15, tzinfo=UTC))
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 15
    assert dt.tzinfo == UTC

    dt = DateTime.instance(pd.Timestamp('2022-01-01 12:30:15'))
    assert dt.year == 2022
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 15

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
    """Test strptime parses strings according to format strings.

    Mutation: strptime returning the pendulum.DateTime unwrapped.
    Oracle: isinstance against opendate's DateTime, and the hand-read
        fields of each input.
    """
    dt = DateTime.strptime(input_str, fmt)
    assert dt.year == expected[0]
    assert dt.month == expected[1]
    assert dt.day == expected[2]
    assert dt.hour == expected[3]
    assert dt.minute == expected[4]
    assert dt.second == expected[5]
    assert isinstance(dt, DateTime)


def test_datetime_rfc3339_format():
    """Test RFC 3339 formatting.

    Mutation: parse stamping LCL rather than UTC on a string with no
        offset.
    Oracle: the hand-written RFC 3339 string.
    """
    dt = DateTime.parse('Fri, 31 Oct 2014 10:55:00')
    assert dt == DateTime(2014, 10, 31, 10, 55, 0, tzinfo=UTC)
    assert dt.rfc3339() == '2014-10-31T10:55:00+00:00'


def test_datetime_utcnow():
    """Test the utcnow class method returns current UTC time.

    Mutation: utcnow labeling the local wall clock as UTC, which is off
        by the local offset.
    Oracle: time.time(), within 2 seconds.
    """
    current_timestamp = time.time()

    dt = DateTime.utcnow()

    assert isinstance(dt, DateTime)

    assert dt.tzinfo == UTC

    dt_timestamp = dt.timestamp()
    time_diff = abs(dt_timestamp - current_timestamp)
    assert time_diff < 2


def test_datetime_astimezone():
    """Test astimezone method for timezone conversion.

    Mutation: astimezone answering a pendulum.DateTime, or a fixed
        -05:00 in June.
    Oracle: hand-computed - 12:00 UTC is 07:00 EST and 08:00 EDT.
    """
    dt_utc = DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)

    dt_est = dt_utc.astimezone(EST)
    assert dt_est.hour == 7
    assert dt_est.tzinfo == EST
    assert isinstance(dt_est, DateTime)

    dt_utc = DateTime(2022, 6, 1, 12, 0, 0, tzinfo=UTC)
    dt_est = dt_utc.astimezone(EST)
    assert dt_est.hour == 8


def test_datetime_in_timezone():
    """Test in_timezone and in_tz methods for timezone conversion.

    Mutation: in_timezone answering a pendulum.DateTime, or in_tz bound
        to a different method.
    Oracle: hand-computed - 12:00 UTC is 07:00 EST and 08:00 EDT.
    """
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


@pytest.mark.parametrize('name', ['Australia/Sydney', 'America/Chicago'])
def test_now_in_a_dateutil_zone(name):
    """Verify now() reads a dateutil zone by name rather than as UTC.

    Mutation: now() handing the zone to pendulum's _safe_timezone, which
        reads a dateutil tzfile as +00:00.
    Oracle: the stdlib's datetime.now in the same zone.
    """
    zone = dateutil.tz.gettz(name)

    value = DateTime.now(zone)

    assert value.utcoffset() == datetime.datetime.now(zone).utcoffset()
    assert value.timezone_name == name


@pytest.mark.parametrize(('name', 'hour', 'offset_hours'), [
    ('Australia/Sydney', 22, 10),
    ('America/Chicago', 7, -5),
    ])
def test_converting_into_a_dateutil_zone(name, hour, offset_hours):
    """Verify in_timezone, in_tz and astimezone honor a dateutil zone.

    Mutation: in_timezone deferring to pendulum, which gives 12:00+00:00;
        astimezone converting self in place, which gives a naive 12:00;
        or an override dropping the calendar.
    Oracle: hand-computed - 2024-07-15 12:00 UTC is 22:00 AEST and 07:00
        CDT.
    """
    zone = dateutil.tz.gettz(name)
    value = DateTime(2024, 7, 15, 12, tzinfo=UTC).calendar('LSE')

    for converted in (value.in_timezone(zone), value.in_tz(zone), value.astimezone(zone)):
        assert converted.hour == hour
        assert converted.utcoffset() == datetime.timedelta(hours=offset_hours)
        assert converted.timezone_name == name
        assert converted._calendar is value._calendar


def test_set_and_replace_with_a_dateutil_zone():
    """Verify set(tz=) and replace(tzinfo=) keep a dateutil zone's wall clock.

    Mutation: replace or create handing the zone to pendulum's
        _safe_timezone, which stamps +00:00 on the wall clock; or replace
        rebuilding only a keyword tzinfo, which leaves the positional
        form at +00:00.
    Oracle: hand-computed - 12:00 in Sydney is +10:00 in July and +11:00
        in January.
    """
    zone = dateutil.tz.gettz('Australia/Sydney')
    value = DateTime(2024, 7, 15, 12, tzinfo=UTC)

    moved_ds = [
        value.replace(tzinfo=zone),
        value.set(tz=zone),
        DateTime(2024, 1, 1, tzinfo=UTC).replace(2024, 7, 15, 12, 0, 0, 0, zone),
        ]

    for moved in moved_ds:
        assert moved.hour == 12
        assert moved.utcoffset() == datetime.timedelta(hours=10)
        assert moved.timezone_name == 'Australia/Sydney'
        assert moved.add(months=6).utcoffset() == datetime.timedelta(hours=11)


@pytest.mark.parametrize(('month', 'hour', 'offset_hours'), [
    (1, 7, -5),
    (7, 8, -4),
    ])
def test_converting_into_a_zone_with_no_name(month, hour, offset_hours):
    """Verify a daylight-saving zone that names nothing converts correctly.

    Mutation: astimezone converting self in place, which gives a naive
        12:00 for a dateutil tzstr; or in_timezone deferring to pendulum,
        which gives 12:00+00:00.
    Oracle: hand-computed - 12:00 UTC is 07:00 EST and 08:00 EDT.
    """
    zone = dateutil.tz.tzstr('EST5EDT')
    value = DateTime(2024, month, 15, 12, tzinfo=UTC)

    for converted in (value.astimezone(zone), value.in_timezone(zone)):
        assert converted.hour == hour
        assert converted.utcoffset() == datetime.timedelta(hours=offset_hours)


def test_in_timezone_sets_a_naive_wall_clock_in_a_dateutil_zone():
    """Verify a naive value's wall clock lands in a foreign zone, calendar kept.

    Mutation: in_timezone handing the zone to pendulum unread, which
        stamps +00:00; or dropping the calendar, which a fixed zone's
        convert loses.
    Oracle: hand-computed - the 12:00 wall clock with each zone's July
        offset, and the calendar object set on the input.
    """
    naive = DateTime(2024, 7, 15, 12).calendar('LSE')
    fixed = datetime.timezone(datetime.timedelta(hours=5))

    moved = naive.in_timezone(dateutil.tz.gettz('Australia/Sydney'))
    moved_fixed = naive.in_timezone(fixed)

    assert moved.isoformat() == '2024-07-15T12:00:00+10:00'
    assert moved.timezone_name == 'Australia/Sydney'
    assert moved_fixed.isoformat() == '2024-07-15T12:00:00+05:00'
    assert moved._calendar is moved_fixed._calendar is naive._calendar


def test_in_timezone_by_name_from_a_zone_with_no_name():
    """Verify a value holding a nameless zone converts to a zone name.

    Mutation: in_timezone sending a str target to pendulum, which stamps
        the 07:00 wall clock with +00:00.
    Oracle: hand-computed - 07:00 EST is 12:00 UTC.
    """
    held = DateTime(2024, 1, 15, 12, tzinfo=UTC).astimezone(dateutil.tz.tzstr('EST5EDT'))

    converted = held.in_timezone('UTC')

    assert (converted.hour, converted.utcoffset()) == (12, datetime.timedelta(0))


def test_a_pytz_zone_in_the_repeated_hour():
    """Verify a pytz zone keeps the second pass of a repeated hour.

    Mutation: handing the pytz zone to the stdlib unrebuilt, whose
        per-offset tzinfo the constructor rebuilds by name at fold 0,
        moving 01:30 EST to 01:30 EDT.
    Oracle: hand-computed - 06:30 UTC on 2024-11-03 is 01:30 EST, after
        the 02:00 EDT fall-back.
    """
    zone = pytz.timezone('America/New_York')
    value = DateTime(2024, 11, 3, 6, 30, tzinfo=UTC)

    converted_ds = [
        value.in_timezone(zone),
        value.astimezone(zone),
        DateTime.fromtimestamp(value.timestamp(), zone),
        ]

    for converted in converted_ds:
        assert (converted.hour, converted.minute) == (1, 30)
        assert converted.utcoffset() == datetime.timedelta(hours=-5)


def test_dateutil_tzlocal_is_the_local_zone(monkeypatch):
    """Verify dateutil's tzlocal settles on LCL, on a daylight-saving host.

    Mutation: dropping the tzlocal case from normalize_timezone, which
        keeps a daylight-saving tzlocal raw, so .tz is None.
    Oracle: the Chicago zone patched in as LCL, with the host's TZ set
        to match, so a host without daylight saving cannot pass it.
    """
    chicago = pendulum.timezone('America/Chicago')
    monkeypatch.setenv('TZ', 'America/Chicago')
    monkeypatch.setattr(opendate.constants, 'LCL', chicago)
    time.tzset()
    try:
        value = DateTime(2024, 1, 15, 12, tzinfo=dateutil.tz.tzlocal())
    finally:
        monkeypatch.undo()
        time.tzset()

    assert value.tz is chicago


def test_naive_subtraction_keeps_the_calendar():
    """Verify naive opendate endpoints keep their calendar in an Interval.

    Mutation: retyping every naive endpoint, opendate ones included,
        which drops the LSE calendar and counts Christmas and Boxing Day.
    Oracle: hand-computed - 2024-12-20 to 12-31 on LSE skips the two
        weekend days and Dec 25-26, the same count the aware pair gives.
    """
    start = DateTime(2024, 12, 20).calendar('LSE')
    end = DateTime(2024, 12, 31).calendar('LSE')
    aware_start = DateTime(2024, 12, 20, tzinfo=UTC).calendar('LSE')
    aware_end = DateTime(2024, 12, 31, tzinfo=UTC).calendar('LSE')

    assert (end - start).b.days == (aware_end - aware_start).b.days == 5


@pytest.mark.parametrize('zone', PARITY_ZONES)
@pytest.mark.parametrize('receiver', PARITY_RECEIVERS)
def test_in_timezone_matches_pendulum_for_zones_pendulum_reads(receiver, zone):
    """Verify in_timezone gives pendulum's result for every zone pendulum reads.

    Mutation: the aware branch converting without the receiver's fold,
        which moves 01:30 EST to 01:30 EDT; or reading a zone name with
        normalize_timezone, which raises on 'utc'.
    Oracle: pendulum's own in_timezone on the same receiver.
    """
    expected = receiver.in_timezone(zone)

    assert parity_key(opendate_twin(receiver).in_timezone(zone)) == parity_key(expected)


@pytest.mark.parametrize('zone', [*PARITY_TZINFOS, None])
@pytest.mark.parametrize('receiver', PARITY_RECEIVERS)
def test_astimezone_matches_pendulum_for_zones_pendulum_owns(receiver, zone):
    """Verify astimezone gives pendulum's result for pendulum's own zones.

    Mutation: the plain copy dropping fold, which reads the repeated hour
        as its first pass; or rebuilding a None target as UTC.
    Oracle: pendulum's own astimezone on the same receiver. For None,
        pendulum keeps the stdlib's nameless local zone, which opendate's
        constructor rebuilds, so only the wall clock, offset and fold
        are compared there.
    """
    expected = receiver.astimezone(zone)

    converted = opendate_twin(receiver).astimezone(zone)

    assert parity_key(converted)[:2] == parity_key(expected)[:2]
    if zone is not None:
        assert converted.timezone_name == expected.timezone_name


@pytest.mark.parametrize('zone', PARITY_ZONES)
@pytest.mark.parametrize('receiver', PARITY_RECEIVERS)
def test_set_and_replace_match_pendulum_for_zones_pendulum_reads(receiver, zone):
    """Verify set and replace give pendulum's result for zones it reads.

    Mutation: replace reading its default tzinfo=True as a zone, or
        create rebuilding a zone name, either of which changes the zone
        or raises.
    Oracle: pendulum's own set and replace on the same receiver.
    """
    ours = opendate_twin(receiver)

    assert parity_key(ours.set(hour=2, minute=30, tz=zone)) == parity_key(
        receiver.set(hour=2, minute=30, tz=zone))
    assert parity_key(ours.replace(tzinfo=zone)) == parity_key(receiver.replace(tzinfo=zone))
    assert parity_key(ours.replace(hour=2, minute=30)) == parity_key(
        receiver.replace(hour=2, minute=30))
    assert parity_key(ours.replace(tzinfo=None)) == parity_key(receiver.replace(tzinfo=None))


@pytest.mark.parametrize('zone', [*PARITY_ZONES, 'local'])
def test_now_matches_pendulum_for_zones_pendulum_reads(zone):
    """Verify now() lands in the zone pendulum's now() picks.

    Mutation: now() rebuilding a str with normalize_timezone, which
        raises on 'utc', or dropping the int-offset path.
    Oracle: pendulum's own now() in the same zone.
    """
    ours, expected = DateTime.now(zone), pendulum.now(zone)

    assert ours.timezone_name == expected.timezone_name
    assert ours.utcoffset() == expected.utcoffset()
    assert abs((ours - expected).in_seconds()) < 5


@pytest.mark.parametrize('zone', PARITY_ZONES)
def test_fromtimestamp_matches_pendulum_for_zones_pendulum_reads(zone):
    """Verify fromtimestamp gives pendulum's result in a repeated hour.

    Mutation: instance() dropping obj.fold, or reading the zone with
        normalize_timezone where pendulum reads a str or an int.
    Oracle: pendulum's own fromtimestamp at 06:30 UTC on 2024-11-03,
        the second pass of 01:30 in New York.
    """
    stamp = pendulum.datetime(2024, 11, 3, 6, 30, tz='UTC').timestamp()

    ours = DateTime.fromtimestamp(stamp, zone)

    assert parity_key(ours) == parity_key(pendulum.DateTime.fromtimestamp(stamp, zone))


def test_fromtimestamp_with_no_zone_is_utc():
    """Verify fromtimestamp reads a None zone as UTC, where pendulum reads local.

    Mutation: passing None on to pendulum's _safe_timezone, which picks
        the local zone, here pinned to Tokyo so a UTC host cannot pass it.
    Oracle: the docstring's None gives UTC, and hand-computed - stamp 0
        is 1970-01-01 00:00 UTC.
    """
    with pendulum.test_local_timezone(pendulum.timezone('Asia/Tokyo')):
        value = DateTime.fromtimestamp(0)

    assert value.isoformat() == '1970-01-01T00:00:00+00:00'
    assert value.timezone_name == 'UTC'


def test_create_reads_a_positional_dateutil_zone():
    """Verify create reads a dateutil zone passed in the eighth slot.

    Mutation: create rebuilding only a tz keyword, which leaves the
        positional zone to pendulum's +00:00.
    Oracle: hand-computed - 12:00 in Sydney in July is +10:00.
    """
    zone = dateutil.tz.gettz('Australia/Sydney')

    value = DateTime.create(2024, 7, 15, 12, 0, 0, 0, zone)

    assert value.utcoffset() == datetime.timedelta(hours=10)
    assert value.timezone_name == 'Australia/Sydney'


def test_time_in_timezone_reads_a_dateutil_zone():
    """Verify Time.in_timezone honors a dateutil zone.

    Mutation: DateTime.in_timezone handing the zone to pendulum unread,
        which leaves the time at 12:00 +00:00.
    Oracle: hand-computed - 12:00 UTC is 21:00 in Tokyo, which keeps no
        daylight saving, so the answer holds on any date.
    """
    moved = Time(12, tzinfo=UTC).in_timezone(dateutil.tz.gettz('Asia/Tokyo'))

    assert (moved.hour, moved.minute) == (21, 0)
    assert moved.tzinfo.key == 'Asia/Tokyo'


def test_today_in_a_nameless_daylight_saving_zone_is_aware():
    """Verify today() keeps a dateutil tzstr zone on its midnight.

    Mutation: today() returning now(tz).start_of('day') as is, whose set()
        reads the raw zone's .tz as None and drops the zone.
    Oracle: the offset tzstr itself reports for that midnight.
    """
    zone = dateutil.tz.tzstr('EST5EDT')

    today = DateTime.today(zone)

    midnight = datetime.datetime(today.year, today.month, today.day)
    assert (today.hour, today.minute, today.second) == (0, 0, 0)
    assert today.utcoffset() == zone.utcoffset(midnight)


def test_astimezone_reads_a_nameless_zone_at_the_converted_instant():
    """Verify astimezone and in_timezone read a hand-written zone by date.

    Mutation: rebuilding the target with no `when`, in astimezone or in
        in_timezone before it, which freezes the zone at its
        utcoffset(None) answer and gives 11:00-05:00.
    Oracle: pendulum's own astimezone, and hand-computed - 16:00 UTC on
        July 1 is 12:00 at the zone's -04:00.
    """
    value = DateTime(2024, 7, 1, 16, tzinfo=UTC)

    converted = value.astimezone(SummerShiftZone())

    assert value.in_timezone(SummerShiftZone()).isoformat() == '2024-07-01T12:00:00-04:00'
    assert converted.isoformat() == '2024-07-01T12:00:00-04:00'
    assert converted.isoformat() == pendulum.instance(value).astimezone(SummerShiftZone()).isoformat()


def test_fromtimestamp_keeps_the_fold():
    """Verify fromtimestamp in a repeated hour picks the second pass.

    Mutation: instance() dropping obj.fold, which reads 01:30 on
        2024-11-03 as the first pass, at -04:00.
    Oracle: pendulum's own fromtimestamp, and hand-computed - 06:30 UTC
        is 01:30 EST, after the 02:00 EDT fall-back.
    """
    stamp = pendulum.datetime(2024, 11, 3, 6, 30, tz='UTC').timestamp()
    zone = pendulum.timezone('America/New_York')

    value = DateTime.fromtimestamp(stamp, zone)

    assert value.isoformat() == pendulum.DateTime.fromtimestamp(stamp, zone).isoformat()
    assert (value.hour, value.minute) == (1, 30)
    assert value.utcoffset() == datetime.timedelta(hours=-5)


def test_subtracting_a_naive_stdlib_datetime():
    """Verify a naive DateTime minus a naive datetime gives an Interval.

    Mutation: rebuilding the Interval from pendulum's raw endpoints,
        which stamps UTC on one and raises TypeError.
    Oracle: pendulum's naive subtraction over the same two values.
    """
    later = datetime.datetime(2024, 1, 15, 12)
    epoch = datetime.datetime(1970, 1, 1)

    span = DateTime.instance(later).replace(tzinfo=None) - epoch

    assert span.in_seconds() == (pendulum.naive(2024, 1, 15, 12) - epoch).in_seconds()
    assert span.start.tzinfo is None


def test_datetime_replace():
    """Test replace method preserves DateTime type and calendar.

    Mutation: replace answering a pendulum.DateTime, or dropping the
        calendar.
    Oracle: DateTime built directly with each replaced field.
    """
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
    """Test date method extracts Date object from DateTime.

    Mutation: date() answering a pendulum.Date, or converting to UTC
        first, which moves 23:59 EST on 12-31 into January.
    Oracle: hand-computed calendar dates of each wall clock.
    """
    dt = DateTime(2022, 1, 15, 12, 30, 45, tzinfo=UTC)

    d = dt.date()
    assert d == Date(2022, 1, 15)
    assert isinstance(d, Date)
    assert type(d).__name__ == 'Date'

    dt = DateTime(2023, 12, 31, 23, 59, 59, tzinfo=EST)
    d = dt.date()
    assert d == Date(2023, 12, 31)


@pytest.mark.parametrize(
    'nat',
    [pd.NaT, np.datetime64('NaT')],
    ids=['pandas', 'numpy'])
def test_datetime_instance_with_nat(nat):
    """Test DateTime.instance answers None for NaT, or raises on raise_err.

    Mutation: dropping the pd.isna guard, so NaT reaches the field reads.
    Oracle: None, and the 'Empty value' ValueError.
    """
    result = DateTime.instance(nat)
    assert result is None

    with pytest.raises(ValueError, match='Empty value'):
        DateTime.instance(nat, raise_err=True)


def test_datetime_instance_with_pandas_timestamp_timezones():
    """Verify a pandas Timestamp's zone arrives as one pendulum reads.

    Mutation: dropping normalize_timezone from DateTime.__new__, which
        leaves the pytz DstTzInfo in place.
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
    """Test DateTime.instance with various numpy datetime64 formats.

    Mutation: converting at a unit coarser than microseconds, which
        drops .123456, or leaving the result naive.
    Oracle: the hand-read fields of each input, and UTC.
    """
    dt1 = DateTime.instance(np.datetime64('2022-01-15'))
    assert dt1.year == 2022
    assert dt1.month == 1
    assert dt1.day == 15
    assert dt1.tzinfo == UTC

    dt2 = DateTime.instance(np.datetime64('2022-01-15T14:30:45'))
    assert dt2.hour == 14
    assert dt2.minute == 30
    assert dt2.second == 45

    dt3 = DateTime.instance(np.datetime64('2022-01-15T14:30:45.123456'))
    assert dt3.microsecond == 123456


def test_instance_injects_utc_on_naive_datetime():
    """Verify DateTime.instance attaches UTC, not merely something.

    Mutation: attaching the local zone in place of UTC.
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
    """Verify a fixed offset stays fixed across a daylight-saving transition.

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

    Mutation: calling `_rust_parse_datetime` before testing the string
        against DATEMATCH, so the general parser reads the 3 of 'T-3'
        as a day of month.
    Oracle: `Date.parse` of the same code, which resolves the codes
        correctly and independently of this path.
    """
    parsed = DateTime.parse(code)

    assert parsed is not None
    assert parsed.date() == Date.parse(code)
    assert (parsed.hour, parsed.minute, parsed.second) == (0, 0, 0)


def test_an_unreadable_zone_is_handed_back_rather_than_raising():
    """Verify a zone pendulum cannot represent survives construction.

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
    """store_calendar returns None when decorated fn returns None.

    Mutation: store_calendar setting the calendar on the result with no
        None check, which raises AttributeError.
    Oracle: None passed through unchanged.
    """

    @store_calendar
    def returns_none(self):
        return None

    assert returns_none(Date(2024, 1, 1)) is None


if __name__ == '__main__':
    pytest.main([__file__])
