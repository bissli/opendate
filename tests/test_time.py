import datetime
import zoneinfo

import numpy as np
import pendulum
import pytest

from opendate import EST, UTC, Date, DateTime, Time, Timezone


def test_time_constructor():
    """Verify an empty constructor gives midnight, as an opendate Time.

    Mutation: the no-argument path in Time.__new__ building a
        pendulum.Time rather than cls.
    Oracle: pendulum.Time(), which is midnight, and isinstance.
    """
    value = Time()
    assert value == pendulum.Time()
    assert isinstance(value, Time)


def test_datetime_to_time():
    """Verify Time.instance stamps UTC on a naive time.

    Mutation: instance leaving a naive time naive, which never equals
        an aware one.
    Oracle: Time(12, 30) built directly in UTC.
    """
    value = pendulum.DateTime(2022, 1, 1, 12, 30)
    assert Time.instance(value.time()) == Time(12, 30, tzinfo=UTC)


@pytest.mark.parametrize(('input_str', 'expected'), [
    # Colon-separated formats
    ('9:30', Time(9, 30, 0, tzinfo=UTC)),
    ('9:30:15', Time(9, 30, 15, tzinfo=UTC)),
    ('9:30:15.751', Time(9, 30, 15, 751000, tzinfo=UTC)),
    ('9:30 AM', Time(9, 30, 0, tzinfo=UTC)),
    ('9:30 pm', Time(21, 30, 0, tzinfo=UTC)),
    ('9:30:15.751 PM', Time(21, 30, 15, 751000, tzinfo=UTC)),
    # Compact formats
    ('0930', Time(9, 30, 0, tzinfo=UTC)),
    ('093015', Time(9, 30, 15, tzinfo=UTC)),
    ('093015,751', Time(9, 30, 15, 751000, tzinfo=UTC)),
    ('093015.751', Time(9, 30, 15, 751000, tzinfo=UTC)),
    ('0930 pm', Time(21, 30, 0, tzinfo=UTC)),
    ('093015,751 PM', Time(21, 30, 15, 751000, tzinfo=UTC)),
    # Dot-separated formats
    ('9.30', Time(9, 30, 0, tzinfo=UTC)),
    ('9.30.15', Time(9, 30, 15, tzinfo=UTC)),
    # Midnight and noon edge cases
    ('1200 AM', Time(0, 0, 0, tzinfo=UTC)),
    ('12:00 PM', Time(12, 0, 0, tzinfo=UTC)),
    ('12:00 AM', Time(0, 0, 0, tzinfo=UTC)),
])
def test_time_parse_formats(input_str, expected):
    """Test Time.parse with various format strings.

    Mutation: the AM/PM rule leaving 12 AM at hour 12, or reading ',751'
        as 751 microseconds.
    Oracle: hand-computed times for each string.
    """
    assert Time.parse(input_str) == expected


@pytest.mark.parametrize('input_str', [
    '9930',
    '0970',
    '930',
    '09301',
])
def test_time_parse_invalid(input_str):
    """Test Time.parse returns None for invalid inputs.

    Mutation: accepting an hour above 23, a minute above 59, or a
        compact form of 3 or 5 digits.
    Oracle: None for each out-of-range or wrong-length input.
    """
    assert Time.parse(input_str) is None


def test_time_instance_basic():
    """Test Time.instance with various input types.

    Mutation: instance stamping UTC on a value that is already a Time.
    Oracle: the input's own None tzinfo, and UTC on the naive stdlib and
        pendulum times.
    """
    assert Time.instance(datetime.time(12, 30, 1)) == Time(12, 30, 1, tzinfo=UTC)
    assert Time.instance(pendulum.Time(12, 30, 1)) == Time(12, 30, 1, tzinfo=UTC)
    assert Time.instance(None) is None

    result = Time.instance(Time(12, 30, 1))
    assert result == Time(12, 30, 1)
    assert result.tzinfo is None


def test_time_instance_reads_a_numpy_datetime64():
    """Verify Time.instance takes the time of day of a numpy datetime64.

    Mutation: instance reading tzinfo and hour off the datetime64 itself,
        which has neither, so it raises AttributeError.
    Oracle: the instance docstring, which lists np.datetime64 as an
        accepted obj and UTC where obj has no zone.
    """
    value = np.datetime64('2022-01-01T12:30:15.250000')
    assert Time.instance(value) == Time(12, 30, 15, 250000, tzinfo=UTC)


def test_time_parse_error_names_the_input():
    """Verify Time.parse's ValueError message carries the rejected string.

    Mutation: a logging-style ('...%s', s) pair passed to ValueError,
        which never fills in the placeholder.
    Oracle: the legacy tc to_time message 'Failed to parse time: ' + s.
    """
    with pytest.raises(ValueError, match='^Failed to parse time: zzz$'):
        Time.parse('zzz', raise_err=True)


def test_time_in_timezone():
    """Test timezone conversion for Time objects.

    Mutation: in_timezone setting tz on the wall clock rather than
        converting, or reading a naive time as local.
    Oracle: hand-computed - Sao Paulo is UTC-3 and Moscow UTC+3, and
        neither observes daylight saving.
    """
    result = Time(12, 0).in_timezone(Timezone('America/Sao_Paulo'))
    assert result.hour == 9
    assert result.minute == 0
    assert result.second == 0

    moscow_noon = Time(12, 0, tzinfo=Timezone('Europe/Moscow'))
    result = moscow_noon.in_timezone(Timezone('America/Sao_Paulo'))
    assert result.hour == 6
    assert result.minute == 0
    assert result.second == 0


def test_combine():
    """Test DateTime.combine with different timezones

    Mutation: combine ignoring tzinfo, which leaves the naive time on
        UTC.
    Oracle: DateTime built directly at 12:30 in each zone.
    """
    day = Date(2022, 1, 1)
    time_of_day = Time(12, 30)

    # Use EST instead of LCL to ensure timezone differs from UTC in CI
    _ = DateTime(2022, 1, 1, 12, 30, tzinfo=EST)
    assert _.tzinfo == EST

    comb = DateTime.combine(day, time_of_day, tzinfo=EST)
    assert comb == _

    comb = DateTime.combine(day, time_of_day, tzinfo=UTC)
    assert comb != _

    _ = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert _.tzinfo == UTC

    comb = DateTime.combine(day, time_of_day, tzinfo=UTC)
    assert comb == _

    comb = DateTime.combine(day, time_of_day, tzinfo=EST)
    assert comb != _


def test_a_driver_offset_survives_construction():
    """Verify a `timetz` value keeps the offset it arrived with.

    Mutation: settling the tzinfo by widening to UTC rather than by
        rebuilding the offset it reports, which relabels 08:01-04:00 as
        08:01+00:00 and moves the instant four hours.
    Oracle: the -4 hour offset the source time reports, against
        08:01:27 unmoved on the wall clock, and a comparison against a
        UTC time of the column, which raises where either side is naive.
    """
    driver_tz = datetime.timezone(datetime.timedelta(hours=-4))
    source = datetime.time(8, 1, 27, tzinfo=driver_tz)

    held = Time.instance(source)

    assert held.utcoffset() == datetime.timedelta(hours=-4)
    assert (held.hour, held.minute, held.second) == (8, 1, 27)
    assert held.tzinfo != UTC
    assert held > Time(11, 0, tzinfo=UTC)


@pytest.mark.parametrize(('text', 'offset_hours'), [
    ('08:01:27-04:00', -4),
    ('08:01:27+05:30', 5.5),
    ('08:01:27+0530', 5.5),
    ('08:01:27Z', 0),
    ('08:01:27', 0),
    ])
def test_parse_keeps_an_offset_the_string_spells_out(text, offset_hours):
    """Verify a parsed time keeps its own offset instead of UTC.

    Mutation: dropping the offset split, so the general parser, which
        reads no offset, leaves prefer_utc_timezone to stamp UTC on
        every row; or reading the minutes off the wrong end, which the
        half-hour rows catch.
    Oracle: the offset each string spells out, against a bare time that
        must still default to UTC.
    """
    parsed = Time.parse(text)

    assert parsed.utcoffset() == datetime.timedelta(hours=offset_hours)
    assert (parsed.hour, parsed.minute, parsed.second) == (8, 1, 27)


def test_parse_does_not_read_a_dash_inside_a_time_as_an_offset():
    """Verify the offset split needs minutes, so a dashed time is safe.

    Mutation: accepting a two-digit offset form, which reads the '45' of
        '14-30-45' as a timezone and answers a time built from '14-30'.
    Oracle: None, since a dashed time is not a supported spelling.
    """
    assert Time.parse('14-30-45') is None
    assert Time.parse('14-30-45', fmt='%H-%M-%S') == Time(14, 30, 45, tzinfo=UTC)


@pytest.mark.parametrize('positional', [False, True])
@pytest.mark.parametrize('driver_tz', [
    zoneinfo.ZoneInfo('America/New_York'),
    datetime.timezone(datetime.timedelta(hours=-4)),
    ])
def test_a_driver_zone_becomes_a_pendulum_one(driver_tz, positional):
    """Verify a time settles its timezone class like a datetime does.

    Mutation: dropping normalize_timezone from Time.__new__, or the
        off-by-one `len(args) > 5` that skips a positional tzinfo.
    Oracle: the pendulum timezone classes themselves, which a driver's
        zoneinfo.ZoneInfo and datetime.timezone are not.
    """
    held = (Time(8, 1, 27, 0, driver_tz) if positional
            else Time(8, 1, 27, tzinfo=driver_tz))

    assert isinstance(held.tzinfo, (pendulum.tz.Timezone,
                                    pendulum.tz.FixedTimezone))
    assert (held.hour, held.minute, held.second) == (8, 1, 27)


if __name__ == '__main__':
    pytest.main([__file__])
