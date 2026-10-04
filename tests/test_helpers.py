import datetime
import zoneinfo

import dateutil.tz
import pendulum
import pytest
import pytz

from opendate import EST, LCL, UTC, DateTime, Time, Timezone, expect_date
from opendate import expect_native_timezone, expect_time
from opendate import expect_utc_timezone, prefer_native_timezone
from opendate import prefer_utc_timezone
from opendate import constants
from opendate.constants import normalize_timezone


def test_timezone_function():
    """Test Timezone function creates proper timezone objects.

    Mutation: Timezone returning a pytz or fixed-offset zone, or mapping
        'GMT' onto 'UTC'.
    Oracle: the IANA keys passed in, read back off each zone.
    """
    tz = Timezone('US/Eastern')
    assert isinstance(tz, zoneinfo.ZoneInfo)
    assert tz.key in {'US/Eastern', 'America/New_York'}

    tz_utc = Timezone('UTC')
    assert tz_utc.key == 'UTC'

    tz_gmt = Timezone('GMT')
    assert tz_gmt.key == 'GMT'


def test_expect_time_decorator():
    """Test expect_time decorator converts time-like objects.

    Mutation: expect_time converting only the first argument, or
        dropping the seconds field.
    Oracle: hand-entered 12:30:45 fields and a Time check on every
        argument.
    """
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
    """Test prefer_utc_timezone adds UTC timezone when missing.

    Mutation: stamping UTC on an aware result too, as force=True does.
    Oracle: the EST zone the aware result carried in.
    """
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
    """Test prefer_native_timezone adds local timezone when missing.

    Mutation: stamping LCL on an aware result too, as force=True does.
    Oracle: the UTC zone the aware result carried in.
    """
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
    """Test expect_utc_timezone forces UTC timezone.

    Mutation: expect_utc_timezone built without force=True, which
        leaves the aware LCL result alone.
    Oracle: the UTC singleton opendate exports.
    """
    @expect_utc_timezone
    def get_datetime():
        return DateTime(2022, 1, 1, 12, 0, 0, tzinfo=LCL)

    result = get_datetime()
    assert result.tzinfo == UTC


def test_expect_native_timezone_decorator():
    """Test expect_native_timezone forces local timezone.

    Mutation: expect_native_timezone built without force=True, which
        leaves the aware UTC result alone.
    Oracle: the LCL zone opendate exports.
    """
    @expect_native_timezone
    def get_datetime():
        return DateTime(2022, 1, 1, 12, 0, 0, tzinfo=UTC)

    result = get_datetime()
    assert result.tzinfo == LCL


def test_decorator_handles_none():
    """Test decorators handle None values gracefully.

    Mutation: expect_date converting None with raise_err=True, or
        prefer_utc_timezone calling replace on a None result.
    Oracle: None in, None out.
    """
    @expect_date
    def func(d):
        return d

    assert func(None) is None

    @prefer_utc_timezone
    def func_tz():
        return None

    assert func_tz() is None


def test_normalize_timezone_does_not_rebuild_what_pendulum_owns(monkeypatch):
    """Verify a timezone pendulum already owns is handed straight back.

    Mutation: dropping the `isinstance(tz, PENDULUM_TIMEZONES)` test, so
        every construction rebuilds a zone pendulum already owns.
    Oracle: a spy over `Timezone` and `fixed_timezone`, which must
        record no call, plus a FixedTimezone named 'deskclock', which a
        rebuild renames to '-04:00'. Identity alone cannot tell: zoneinfo
        and `fixed_timezone` cache, so a rebuild returns the same object.
    """
    calls = []
    monkeypatch.setattr(constants, 'Timezone', lambda name: calls.append(name))
    monkeypatch.setattr(
        pendulum.tz,
        'fixed_timezone',
        lambda seconds: calls.append(seconds))

    assert normalize_timezone(UTC) is UTC
    assert normalize_timezone(EST) is EST
    assert normalize_timezone(None) is None
    assert calls == []

    named = pendulum.tz.FixedTimezone(-14400, name='deskclock')
    assert normalize_timezone(named).name == 'deskclock'
    assert calls == []


def test_normalize_timezone_keeps_a_named_zone_by_name():
    """Verify a named zone is rebuilt by name, not by its offset today.

    Mutation: settling every unrecognized tzinfo on the offset it
        reports, which pins one season's offset onto the zone.
    Oracle: hand-computed - America/New_York is -05:00 in January and
        -04:00 in July, which one fixed offset cannot both be.
    """
    rebuilt = normalize_timezone(zoneinfo.ZoneInfo('America/New_York'))

    assert isinstance(rebuilt, pendulum.tz.Timezone)
    assert rebuilt.name == 'America/New_York'

    january = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=rebuilt)
    july = datetime.datetime(2026, 7, 15, 12, 0, tzinfo=rebuilt)
    assert january.utcoffset() == datetime.timedelta(hours=-5)
    assert july.utcoffset() == datetime.timedelta(hours=-4)


def test_normalize_timezone_names_a_dateutil_zone_rather_than_freezing_it():
    """Verify a dateutil zone is rebuilt by name, so it still tracks DST.

    Mutation: dropping the `_filename` lookup from zone_name, which
        sends the zone to the offset branch and freezes one season onto
        it - or, with the vary guard in place, hands it back unrebuilt.
    Oracle: hand-computed - America/New_York is -04:00 in August and
        -05:00 in January, read off ONE rebuilt zone object, which a
        single frozen offset cannot be.
    """
    zone = dateutil.tz.gettz('America/New_York')
    assert zone.utcoffset(None) is None

    rebuilt = normalize_timezone(zone, datetime.datetime(2026, 8, 28, 12, 0))

    assert isinstance(rebuilt, pendulum.tz.Timezone)
    assert rebuilt.name == 'America/New_York'
    august = datetime.datetime(2026, 8, 28, 12, 0, tzinfo=rebuilt)
    january = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=rebuilt)
    assert august.utcoffset() == datetime.timedelta(hours=-4)
    assert january.utcoffset() == datetime.timedelta(hours=-5)


def test_normalize_timezone_refuses_to_freeze_a_zone_whose_offset_moves():
    """Verify a nameless daylight-saving zone is handed back, not frozen.

    Mutation: dropping the January-against-July guard, which freezes the
        zone and makes a July value out of a January one report -05:00
        where the zone itself says -04:00.
    Oracle: identity - the same object back - plus the zone's own
        differing offsets in January and July.
    """
    class Varying(datetime.tzinfo):
        """A daylight-saving zone naming itself nowhere."""

        def utcoffset(self, dt):
            return datetime.timedelta(hours=-5) + self.dst(dt)

        def dst(self, dt):
            if dt is None or dt.tzinfo is None:
                return datetime.timedelta(0)
            summer = 3 < dt.month < 11
            return datetime.timedelta(hours=1) if summer else datetime.timedelta(0)

        def tzname(self, dt):
            return 'VAR'

    zone = Varying()
    reference = datetime.datetime(2026, 7, 15, 12, 0, tzinfo=zone)
    assert zone.utcoffset(reference) == datetime.timedelta(hours=-4)
    assert zone.utcoffset(reference.replace(month=1)) == datetime.timedelta(hours=-5)

    assert normalize_timezone(zone, reference) is zone


def test_normalize_timezone_reads_a_pytz_zone_by_its_zone_attribute():
    """Verify a pytz zone is rebuilt by name, through `.zone`.

    Mutation: dropping the `getattr(tz, 'zone', None)` half of the name
        lookup, which sends every pytz zone to the offset branch and
        freezes one season's offset onto it.
    Oracle: the zone name itself, plus -05:00 in January against -04:00
        in July, which a frozen offset cannot both be.
    """
    rebuilt = normalize_timezone(pytz.timezone('America/New_York'))

    assert isinstance(rebuilt, pendulum.tz.Timezone)
    assert rebuilt.name == 'America/New_York'

    january = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=rebuilt)
    july = datetime.datetime(2026, 7, 15, 12, 0, tzinfo=rebuilt)
    assert january.utcoffset() == datetime.timedelta(hours=-5)
    assert july.utcoffset() == datetime.timedelta(hours=-4)


@pytest.mark.parametrize(
    ('offset_hours', 'expected_seconds'),
    [
        (-4, -14400),
        (5.5, 19800),
        ])
def test_normalize_timezone_settles_a_fixed_offset(offset_hours, expected_seconds):
    """Verify a zone naming nothing settles on the offset it reports.

    Mutation: reading the offset as whole hours, or dropping the sign,
        either of which the half-hour row catches.
    Oracle: hand-computed second counts, -14400 and 19800.
    """
    source = datetime.timezone(datetime.timedelta(hours=offset_hours))

    rebuilt = normalize_timezone(source)

    assert isinstance(rebuilt, pendulum.tz.FixedTimezone)
    assert rebuilt.utcoffset(None).total_seconds() == expected_seconds


def test_normalize_timezone_settles_a_zero_offset_on_utc():
    """Verify a zero-offset zone lands on UTC rather than a look-alike.

    Mutation: returning a FixedTimezone(0), which carries the same
        offset but is not the UTC every other entry point produces, so
        one column would hold two zone objects for one zone.
    Oracle: identity against the UTC singleton opendate exports.
    """
    assert normalize_timezone(datetime.timezone.utc) is UTC
    assert normalize_timezone(datetime.timezone(datetime.timedelta(0))) is UTC


def test_normalize_timezone_accepts_a_zone_name():
    """Verify a string names a zone rather than being handed back as one.

    Mutation: falling through to the offset branch for a str, which has
        no utcoffset and would raise AttributeError.
    Oracle: the rebuilt zone's own name, against the string given.
    """
    rebuilt = normalize_timezone('America/New_York')

    assert isinstance(rebuilt, pendulum.tz.Timezone)
    assert rebuilt.name == 'America/New_York'


if __name__ == '__main__':
    pytest.main([__file__])
