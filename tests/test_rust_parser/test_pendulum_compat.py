"""Pendulum parsing tests - ported from pendulum/tests/parsing/test_parsing.py.

These tests verify compatibility with pendulum's date/time parsing.
"""

from datetime import datetime

import pytest

from date._opendate import isoparse, parse


def _parse_to_datetime(result, default=None):
    """Convert ParseResult to datetime for comparison.

    Args:
        result: ParseResult from parser
        default: Optional default datetime to fill missing components
    """
    if result is None:
        return None

    # Handle tuple from fuzzy_with_tokens
    if isinstance(result, tuple):
        result = result[0]

    # Use defaults if provided, otherwise use standard defaults
    if default:
        year = result.year if result.year is not None else default.year
        month = result.month if result.month is not None else default.month
        day = result.day if result.day is not None else default.day
        hour = result.hour if result.hour is not None else default.hour
        minute = result.minute if result.minute is not None else default.minute
        second = result.second if result.second is not None else default.second
        microsecond = result.microsecond if result.microsecond is not None else default.microsecond
    else:
        year = result.year if result.year is not None else 1
        month = result.month if result.month is not None else 1
        day = result.day if result.day is not None else 1
        hour = result.hour if result.hour is not None else 0
        minute = result.minute if result.minute is not None else 0
        second = result.second if result.second is not None else 0
        microsecond = result.microsecond if result.microsecond is not None else 0

    return datetime(year, month, day, hour, minute, second, microsecond)


class TestPendulumYearFormats:
    """Test year and year-month formats."""

    def test_y(self):
        """Test year only: 2016."""
        result = isoparse('2016')
        assert result.year == 2016
        assert result.month == 1
        assert result.day == 1

    def test_ym(self):
        """Test year-month: 2016-10."""
        result = isoparse('2016-10')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1

    def test_ymd(self):
        """Test year-month-day: 2016-10-06."""
        result = isoparse('2016-10-06')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6

    def test_ymd_one_character(self):
        """Test single digit month/day: 2016-2-6."""
        result = parse('2016-2-6', fuzzy=True)
        assert result.year == 2016
        assert result.month == 2
        assert result.day == 6


class TestPendulumDatetimeFormats:
    """Test datetime formats."""

    def test_ymd_hms(self):
        """Test datetime: 2016-10-06 12:34:56."""
        result = parse('2016-10-06 12:34:56', fuzzy=True)
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.microsecond is None or result.microsecond == 0

    def test_ymd_hms_microseconds(self):
        """Test datetime with microseconds: 2016-10-06 12:34:56.123456."""
        result = parse('2016-10-06 12:34:56.123456', fuzzy=True)
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.microsecond == 123456


class TestPendulumRFC3339:
    """Test RFC 3339 formats."""

    def test_rfc_3339(self):
        """Test RFC 3339: 2016-10-06T12:34:56+05:30."""
        result = isoparse('2016-10-06T12:34:56+05:30')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.tzoffset == 19800  # 5*3600 + 30*60

    def test_rfc_3339_extended(self):
        """Test RFC 3339 with microseconds: 2016-10-06T12:34:56.123456+05:30."""
        result = isoparse('2016-10-06T12:34:56.123456+05:30')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.microsecond == 123456
        assert result.tzoffset == 19800

    def test_rfc_3339_extended_small_microseconds(self):
        """Test RFC 3339 with small microseconds: 2016-10-06T12:34:56.000123+05:30."""
        result = isoparse('2016-10-06T12:34:56.000123+05:30')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.microsecond == 123
        assert result.tzoffset == 19800

    def test_rfc_3339_extended_nanoseconds(self):
        """Test RFC 3339 with nanoseconds (truncated): 2016-10-06T12:34:56.123456789+05:30."""
        result = isoparse('2016-10-06T12:34:56.123456789+05:30')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.microsecond == 123456  # Truncated to microseconds
        assert result.tzoffset == 19800


class TestPendulumISO8601Date:
    """Test ISO 8601 date formats."""

    def test_iso_8601_date_year(self):
        """Test ISO date year only: 2012."""
        result = isoparse('2012')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 1

    def test_iso_8601_date_full(self):
        """Test ISO date full: 2012-05-03."""
        result = isoparse('2012-05-03')
        assert result.year == 2012
        assert result.month == 5
        assert result.day == 3

    def test_iso_8601_date_compact(self):
        """Test ISO date compact: 20120503."""
        result = isoparse('20120503')
        assert result.year == 2012
        assert result.month == 5
        assert result.day == 3

    def test_iso_8601_date_yearmonth(self):
        """Test ISO date year-month: 2012-05."""
        result = isoparse('2012-05')
        assert result.year == 2012
        assert result.month == 5
        assert result.day == 1


class TestPendulumISO8601Datetime:
    """Test ISO 8601 datetime formats."""

    def test_iso8601_datetime_hour(self):
        """Test ISO datetime with hour: 2016-10-01T14."""
        result = isoparse('2016-10-01T14')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14

    def test_iso8601_datetime_hour_minute(self):
        """Test ISO datetime with hour:minute: 2016-10-01T14:30."""
        result = isoparse('2016-10-01T14:30')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14
        assert result.minute == 30

    def test_iso8601_datetime_compact_hour(self):
        """Test ISO datetime compact with hour: 20161001T14."""
        result = isoparse('20161001T14')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14

    def test_iso8601_datetime_compact_hour_minute(self):
        """Test ISO datetime compact: 20161001T1430."""
        result = isoparse('20161001T1430')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14
        assert result.minute == 30

    def test_iso8601_datetime_compact_with_tz(self):
        """Test ISO datetime compact with tz: 20161001T1430+0530."""
        result = isoparse('20161001T1430+0530')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14
        assert result.minute == 30
        assert result.tzoffset == 19800

    def test_iso8601_datetime_full_precision(self):
        """Test ISO datetime full precision: 2008-09-03T20:56:35.450686+01."""
        result = isoparse('2008-09-03T20:56:35.450686+01')
        assert result.year == 2008
        assert result.month == 9
        assert result.day == 3
        assert result.hour == 20
        assert result.minute == 56
        assert result.second == 35
        assert result.microsecond == 450686
        assert result.tzoffset == 3600


class TestPendulumISO8601WeekNumber:
    """Test ISO 8601 week number formats (YYYY-Www)."""

    def test_iso8601_week_number(self):
        """Test ISO week: 2012-W05."""
        result = isoparse('2012-W05')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 30

    def test_iso8601_week_number_compact(self):
        """Test ISO week compact: 2012W05."""
        result = isoparse('2012W05')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 30

    def test_iso8601_week_number_long_year(self):
        """Test ISO week in long year: 2015W53."""
        result = isoparse('2015W53')
        assert result.year == 2015
        assert result.month == 12
        assert result.day == 28

    def test_iso8601_week_number_with_day(self):
        """Test ISO week with day: 2012-W05-5."""
        result = isoparse('2012-W05-5')
        assert result.year == 2012
        assert result.month == 2
        assert result.day == 3

    def test_iso8601_week_number_with_day_compact(self):
        """Test ISO week with day compact: 2012W055."""
        result = isoparse('2012W055')
        assert result.year == 2012
        assert result.month == 2
        assert result.day == 3

    def test_iso8601_week_number_year_boundary_end(self):
        """Test ISO week year boundary: 2009-W53-7."""
        result = isoparse('2009-W53-7')
        assert result.year == 2010
        assert result.month == 1
        assert result.day == 3

    def test_iso8601_week_number_year_boundary_start(self):
        """Test ISO week year boundary: 2009-W01-1."""
        result = isoparse('2009-W01-1')
        assert result.year == 2008
        assert result.month == 12
        assert result.day == 29

    def test_iso8601_week_number_2026W36(self):
        """Test ISO week bug #916: 2026W36."""
        result = isoparse('2026W36')
        assert result.year == 2026
        assert result.month == 8
        assert result.day == 31

    def test_iso8601_week_number_with_time(self):
        """Test ISO week with time: 2012-W05T09."""
        result = isoparse('2012-W05T09')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 30
        assert result.hour == 9

    def test_iso8601_week_number_with_time_compact(self):
        """Test ISO week with time compact: 2012W05T09."""
        result = isoparse('2012W05T09')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 30
        assert result.hour == 9


class TestPendulumISO8601Ordinal:
    """Test ISO 8601 ordinal date formats (YYYY-DDD)."""

    def test_iso8601_ordinal(self):
        """Test ISO ordinal: 2012-007."""
        result = isoparse('2012-007')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 7

    def test_iso8601_ordinal_compact(self):
        """Test ISO ordinal compact: 2012007."""
        result = isoparse('2012007')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 7


class TestPendulumISO8601Time:
    """Test ISO 8601 time-only formats."""

    def test_iso8601_time_colon(self):
        """Test ISO time: 20:12:05."""
        result = parse('20:12:05', fuzzy=True)
        assert result.hour == 20
        assert result.minute == 12
        assert result.second == 5

    def test_iso8601_time_microseconds(self):
        """Test ISO time with microseconds: 20:12:05.123456."""
        result = parse('20:12:05.123456', fuzzy=True)
        assert result.hour == 20
        assert result.minute == 12
        assert result.second == 5
        assert result.microsecond == 123456


class TestPendulumEdgeCases:
    """Test pendulum edge cases."""

    def test_single_digit_day(self):
        """Test single digit day: 2013-11-1."""
        result = parse('2013-11-1', fuzzy=True)
        assert result.year == 2013
        assert result.month == 11
        assert result.day == 1

    @pytest.mark.xfail(reason='Pendulum interprets 10-01-01 as YY-MM-DD, dateutil as MM-DD-YY')
    def test_two_digit_year_10(self):
        """Test two digit year: 10-01-01."""
        result = parse('10-01-01', fuzzy=True)
        assert result.year == 2010
        assert result.month == 1
        assert result.day == 1

    @pytest.mark.xfail(reason='Pendulum interprets 31-01-01 as YY-MM-DD, dateutil as DD-MM-YY')
    def test_two_digit_year_31(self):
        """Test two digit year: 31-01-01."""
        result = parse('31-01-01', fuzzy=True)
        assert result.year == 2031
        assert result.month == 1
        assert result.day == 1

    def test_two_digit_year_32(self):
        """Test two digit year: 32-01-01."""
        result = parse('32-01-01', fuzzy=True)
        assert result.year == 2032
        assert result.month == 1
        assert result.day == 1


class TestPendulumStrict:
    """Test strict vs non-strict parsing."""

    def test_non_strict_format(self):
        """Test non-strict format: 4 Aug 2015 - 11:20 PM."""
        result = parse('4 Aug 2015 - 11:20 PM', fuzzy=True)
        assert result.year == 2015
        assert result.month == 8
        assert result.day == 4
        assert result.hour == 23
        assert result.minute == 20


class TestPendulumExifEdgeCase:
    """Test EXIF date format edge case."""

    @pytest.mark.xfail(reason='EXIF format (colon date separators) is pendulum-specific, not supported by dateutil')
    def test_exif_edge_case(self):
        """Test EXIF format: 2016:12:26 15:45:28."""
        result = parse('2016:12:26 15:45:28', fuzzy=True)
        assert result.year == 2016
        assert result.month == 12
        assert result.day == 26
        assert result.hour == 15
        assert result.minute == 45
        assert result.second == 28


class TestPendulumTimezones:
    """Test timezone parsing."""

    def test_utc_z(self):
        """Test UTC with Z."""
        result = isoparse('2016-10-06T12:34:56Z')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.tzoffset == 0

    def test_positive_offset(self):
        """Test positive timezone offset."""
        result = isoparse('2016-10-06T12:34:56+05:30')
        assert result.tzoffset == 19800

    def test_negative_offset(self):
        """Test negative timezone offset."""
        result = isoparse('2016-10-06T12:34:56-08:00')
        assert result.tzoffset == -28800

    def test_hour_only_offset(self):
        """Test hour-only timezone offset."""
        result = isoparse('2016-10-06T12:34:56+05')
        assert result.tzoffset == 18000

    def test_compact_offset(self):
        """Test compact timezone offset."""
        result = isoparse('2016-10-06T12:34:56+0530')
        assert result.tzoffset == 19800
