"""ISO 8601 parser tests - ported from dateutil test_isoparser.py.

These tests verify comprehensive ISO 8601 date/time parsing.
"""

import pytest

from opendate._opendate import IsoParser, isoparse


class TestIsoparserDates:
    """Test ISO 8601 date parsing."""

    def test_iso_date_yyyy(self):
        """Test year only: 2024."""
        r = isoparse('2024')
        assert r.year == 2024

    def test_iso_date_yyyy_mm(self):
        """Test year-month: 2024-01."""
        r = isoparse('2024-01')
        assert r.year == 2024
        assert r.month == 1

    def test_iso_date_yyyy_mm_dd(self):
        """Test full date: 2024-01-15."""
        r = isoparse('2024-01-15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_iso_date_compact_yyyymmdd(self):
        """Test compact date: 20240115."""
        r = isoparse('20240115')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_iso_date_compact_yyyymm(self):
        """Test compact year-month with separator: 2024-01."""
        # Note: 6-digit YYYYMM is ambiguous (could be YYMMDD)
        # Use hyphenated form for unambiguous year-month
        r = isoparse('2024-01')
        assert r.year == 2024
        assert r.month == 1


class TestIsoparserDatetimes:
    """Test ISO 8601 datetime parsing."""

    def test_iso_datetime_t_separator(self):
        """Test datetime with T: 2024-01-15T10:30:45."""
        r = isoparse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_iso_datetime_space_separator(self):
        """Test datetime with space: 2024-01-15 10:30:45."""
        parser = IsoParser(sep=' ')
        r = parser.isoparse('2024-01-15 10:30:45')
        assert r.year == 2024
        assert r.hour == 10

    def test_iso_datetime_hour_only(self):
        """Test datetime with hour only: 2024-01-15T10."""
        r = isoparse('2024-01-15T10')
        assert r.year == 2024
        assert r.hour == 10

    def test_iso_datetime_hour_minute(self):
        """Test datetime with hour:minute: 2024-01-15T10:30."""
        r = isoparse('2024-01-15T10:30')
        assert r.year == 2024
        assert r.hour == 10
        assert r.minute == 30

    def test_iso_datetime_compact(self):
        """Test compact datetime: 20240115T103045."""
        r = isoparse('20240115T103045')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestIsoparserTimes:
    """Test ISO 8601 time parsing."""

    def test_iso_time_hh(self):
        """Test hour only: 10."""
        parser = IsoParser()
        r = parser.parse_isotime('10')
        assert r.hour == 10

    def test_iso_time_hhmm(self):
        """Test hour:minute: 10:30."""
        parser = IsoParser()
        r = parser.parse_isotime('10:30')
        assert r.hour == 10
        assert r.minute == 30

    def test_iso_time_hhmmss(self):
        """Test hour:minute:second: 10:30:45."""
        parser = IsoParser()
        r = parser.parse_isotime('10:30:45')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_iso_time_compact_hhmm(self):
        """Test compact time: 1030."""
        parser = IsoParser()
        r = parser.parse_isotime('1030')
        assert r.hour == 10
        assert r.minute == 30

    def test_iso_time_compact_hhmmss(self):
        """Test compact time: 103045."""
        parser = IsoParser()
        r = parser.parse_isotime('103045')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestIsoparserMicroseconds:
    """Test ISO 8601 microsecond parsing."""

    def test_iso_microseconds_6_digits(self):
        """Test 6-digit microseconds: .123456."""
        r = isoparse('2024-01-15T10:30:45.123456')
        assert r.microsecond == 123456

    def test_iso_microseconds_3_digits(self):
        """Test 3-digit milliseconds: .123."""
        r = isoparse('2024-01-15T10:30:45.123')
        assert r.microsecond == 123000

    def test_iso_microseconds_1_digit(self):
        """Test 1-digit fractional: .1."""
        r = isoparse('2024-01-15T10:30:45.1')
        assert r.microsecond == 100000

    def test_iso_microseconds_comma(self):
        """Test comma decimal separator: ,123456."""
        r = isoparse('2024-01-15T10:30:45,123456')
        assert r.microsecond == 123456

    def test_iso_microseconds_9_digits(self):
        """Test 9-digit nanoseconds (truncated): .123456789."""
        r = isoparse('2024-01-15T10:30:45.123456789')
        # Should be truncated to 6 digits
        assert r.microsecond == 123456


class TestIsoparserTimezones:
    """Test ISO 8601 timezone parsing."""

    def test_iso_tz_z(self):
        """Test Z (UTC): 2024-01-15T10:30:45Z."""
        r = isoparse('2024-01-15T10:30:45Z')
        assert r.tzoffset == 0
        assert r.tzname == 'UTC'

    def test_iso_tz_plus_offset(self):
        """Test positive offset: +05:30."""
        r = isoparse('2024-01-15T10:30:45+05:30')
        assert r.tzoffset == 5 * 3600 + 30 * 60

    def test_iso_tz_minus_offset(self):
        """Test negative offset: -08:00."""
        r = isoparse('2024-01-15T10:30:45-08:00')
        assert r.tzoffset == -8 * 3600

    def test_iso_tz_compact_plus(self):
        """Test compact positive offset: +0530."""
        r = isoparse('2024-01-15T10:30:45+0530')
        assert r.tzoffset == 5 * 3600 + 30 * 60

    def test_iso_tz_compact_minus(self):
        """Test compact negative offset: -0800."""
        r = isoparse('2024-01-15T10:30:45-0800')
        assert r.tzoffset == -8 * 3600

    def test_iso_tz_hour_only_plus(self):
        """Test hour-only positive offset: +05."""
        r = isoparse('2024-01-15T10:30:45+05')
        assert r.tzoffset == 5 * 3600

    def test_iso_tz_hour_only_minus(self):
        """Test hour-only negative offset: -08."""
        r = isoparse('2024-01-15T10:30:45-08')
        assert r.tzoffset == -8 * 3600

    def test_iso_tz_zero_offset(self):
        """Test zero offset: +00:00."""
        r = isoparse('2024-01-15T10:30:45+00:00')
        assert r.tzoffset == 0

    def test_iso_tz_minus_zero(self):
        """Test -00:00 offset."""
        r = isoparse('2024-01-15T10:30:45-00:00')
        assert r.tzoffset == 0


class TestIsoparserClass:
    """Test IsoParser class."""

    def test_isoparser_default(self):
        """Test default IsoParser."""
        parser = IsoParser()
        r = parser.isoparse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.hour == 10

    def test_isoparser_custom_sep(self):
        """Test IsoParser with custom separator."""
        parser = IsoParser(sep=' ')
        r = parser.isoparse('2024-01-15 10:30:45')
        assert r.year == 2024
        assert r.hour == 10

    def test_isoparser_parse_isodate(self):
        """Test parse_isodate method."""
        parser = IsoParser()
        r = parser.parse_isodate('2024-01-15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_isoparser_parse_isotime(self):
        """Test parse_isotime method."""
        parser = IsoParser()
        r = parser.parse_isotime('10:30:45')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestIsoparserEdgeCases:
    """Test ISO parser edge cases."""

    def test_iso_midnight(self):
        """Test midnight: 00:00:00."""
        r = isoparse('2024-01-15T00:00:00')
        assert r.hour == 0
        assert r.minute == 0
        assert r.second == 0

    def test_iso_end_of_day(self):
        """Test end of day: 23:59:59."""
        r = isoparse('2024-01-15T23:59:59')
        assert r.hour == 23
        assert r.minute == 59
        assert r.second == 59

    def test_iso_leap_year_feb_29(self):
        """Test Feb 29 in leap year."""
        r = isoparse('2024-02-29')
        assert r.year == 2024
        assert r.month == 2
        assert r.day == 29

    def test_iso_min_year(self):
        """Test minimum year: 0001."""
        r = isoparse('0001-01-01')
        assert r.year == 1

    def test_iso_max_common_year(self):
        """Test year 9999."""
        r = isoparse('9999-12-31')
        assert r.year == 9999
        assert r.month == 12
        assert r.day == 31

    def test_iso_with_microseconds_and_tz(self):
        """Test full ISO with microseconds and timezone."""
        r = isoparse('2024-01-15T10:30:45.123456+05:30')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45
        assert r.microsecond == 123456
        assert r.tzoffset == 5 * 3600 + 30 * 60


class TestIsoparserFormats:
    """Test various ISO format variants."""

    def test_all_months(self):
        """Test parsing all months."""
        for month in range(1, 13):
            date_str = f'2024-{month:02d}-15'
            r = isoparse(date_str)
            assert r.month == month, f'Failed for month {month}'

    def test_all_days(self):
        """Test parsing various days of month."""
        for day in [1, 10, 15, 20, 28, 30, 31]:
            date_str = f'2024-01-{day:02d}'
            r = isoparse(date_str)
            assert r.day == day, f'Failed for day {day}'

    def test_various_hours(self):
        """Test parsing various hours."""
        for hour in [0, 6, 12, 18, 23]:
            time_str = f'2024-01-15T{hour:02d}:30:45'
            r = isoparse(time_str)
            assert r.hour == hour, f'Failed for hour {hour}'

    def test_various_timezones(self):
        """Test various timezone offsets."""
        offsets = [
            ('+00:00', 0),
            ('+01:00', 3600),
            ('+05:30', 5 * 3600 + 30 * 60),
            ('+12:00', 12 * 3600),
            ('-05:00', -5 * 3600),
            ('-08:00', -8 * 3600),
            ('-12:00', -12 * 3600),
        ]
        for offset_str, expected in offsets:
            r = isoparse(f'2024-01-15T10:30:45{offset_str}')
            assert r.tzoffset == expected, f'Failed for offset {offset_str}'


class TestIsoparserInvalidFormats:
    """Test that invalid formats are rejected."""

    def test_time_trailing_digit(self):
        """Test that trailing digit is rejected: 09301 (5 digits)."""
        parser = IsoParser()
        with pytest.raises(Exception):
            parser.parse_isotime('09301')

    def test_time_trailing_text(self):
        """Test that trailing text is rejected: 14:30extra."""
        parser = IsoParser()
        with pytest.raises(Exception):
            parser.parse_isotime('14:30extra')

    def test_time_ampm_suffix(self):
        """Test that AM/PM suffixes are rejected (ISO doesn't support)."""
        parser = IsoParser()
        with pytest.raises(Exception):
            parser.parse_isotime('0930 pm')
        with pytest.raises(Exception):
            parser.parse_isotime('09:30 pm')
        with pytest.raises(Exception):
            parser.parse_isotime('09:30am')

    def test_time_microseconds_trailing_text(self):
        """Test that trailing text after microseconds is rejected."""
        parser = IsoParser()
        with pytest.raises(Exception):
            parser.parse_isotime('14:30:45.123extra')

    def test_datetime_trailing_text(self):
        """Test that datetime with trailing text is rejected."""
        with pytest.raises(Exception):
            isoparse('2024-01-15T09:30extra')
        with pytest.raises(Exception):
            isoparse('2024-01-15T093015X')

    def test_time_trailing_whitespace_allowed(self):
        """Test that trailing whitespace IS allowed."""
        parser = IsoParser()
        r = parser.parse_isotime('14:30 ')
        assert r.hour == 14
        assert r.minute == 30

        r = parser.parse_isotime('14:30:45\t')
        assert r.hour == 14
        assert r.minute == 30
        assert r.second == 45
