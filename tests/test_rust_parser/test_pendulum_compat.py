"""Pendulum parsing tests.

Ported from pendulum/tests/parsing/test_parsing.py. These tests verify
compatibility with pendulum's date/time parsing.
"""

import pytest

from opendate._opendate import isoparse, parse


class TestPendulumYearFormats:
    """Test year and year-month formats.
    """

    @pytest.mark.parametrize(
        ('text', 'year', 'month', 'day'),
        [
            ('2016', 2016, 1, 1),
            ('2016-10', 2016, 10, 1),
            ('2016-10-06', 2016, 10, 6),
            ])
    def test_year_formats(self, text, year, month, day):
        """Test year, year-month and year-month-day.

        Mutation: a missing month or day left None in place of 1.
        Oracle: fields hand-read from the input. Missing fields are 1.
        """
        result = isoparse(text)
        assert result.year == year
        assert result.month == month
        assert result.day == day

    def test_ymd_one_character(self):
        """Test single digit month/day: 2016-2-6.

        Mutation: a 1-digit month or day field rejected.
        Oracle: fields hand-read from the literal input.
        """
        result = parse('2016-2-6', fuzzy=True)
        assert result.year == 2016
        assert result.month == 2
        assert result.day == 6


class TestPendulumDatetimeFormats:
    """Test datetime formats.
    """

    def test_ymd_hms(self):
        """Test datetime: 2016-10-06 12:34:56.

        Mutation: a nonzero microsecond made up when the input has none.
        Oracle: fields hand-read from the literal input.
        """
        result = parse('2016-10-06 12:34:56', fuzzy=True)
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.microsecond is None or result.microsecond == 0

    def test_ymd_hms_microseconds(self):
        """Test datetime with microseconds: 2016-10-06 12:34:56.123456.

        Mutation: the fraction dropped or scaled as milliseconds.
        Oracle: fields hand-read from the literal input.
        """
        result = parse('2016-10-06 12:34:56.123456', fuzzy=True)
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.microsecond == 123456


class TestPendulumRFC3339:
    """Test RFC 3339 formats.
    """

    def test_rfc_3339(self):
        """Test RFC 3339: 2016-10-06T12:34:56+05:30.

        Mutation: the offset sign flipped or its minutes dropped.
        Oracle: fields hand-read from the input. +05:30 is 19800 s.
        """
        result = isoparse('2016-10-06T12:34:56+05:30')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.tzoffset == 19800

    @pytest.mark.parametrize(
        ('text', 'microsecond'),
        [
            ('2016-10-06T12:34:56.123456+05:30', 123456),
            ('2016-10-06T12:34:56.000123+05:30', 123),
            ('2016-10-06T12:34:56.123456789+05:30', 123456),
            ])
    def test_rfc_3339_extended(self, text, microsecond):
        """Test RFC 3339 with 6-digit, zero-led and 9-digit fractions.

        Mutation: leading zeros of the fraction stripped (.000123 as
            123000), or a 9-digit fraction rounded or rejected.
        Oracle: hand-scaled fractions. Digits past the sixth truncate.
            +05:30 is 19800 s.
        """
        result = isoparse(text)
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.microsecond == microsecond
        assert result.tzoffset == 19800


class TestPendulumISO8601Date:
    """Test ISO 8601 date formats.
    """

    @pytest.mark.parametrize(
        ('text', 'month', 'day'),
        [
            ('2012', 1, 1),
            ('2012-05-03', 5, 3),
            ('20120503', 5, 3),
            ('2012-05', 5, 1),
            ])
    def test_iso_8601_date(self, text, month, day):
        """Test year, full, compact and year-month dates.

        Mutation: a compact date split at the wrong offsets, or a missing
            month or day left None in place of 1.
        Oracle: fields hand-read from the input. Missing fields are 1.
        """
        result = isoparse(text)
        assert result.year == 2012
        assert result.month == month
        assert result.day == day


class TestPendulumISO8601Datetime:
    """Test ISO 8601 datetime formats.
    """

    def test_iso8601_datetime_hour(self):
        """Test ISO datetime with hour: 2016-10-01T14.

        Mutation: a time part with only the hour rejected.
        Oracle: fields hand-read from the literal input.
        """
        result = isoparse('2016-10-01T14')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14

    def test_iso8601_datetime_hour_minute(self):
        """Test ISO datetime with hour:minute: 2016-10-01T14:30.

        Mutation: a time part without seconds rejected.
        Oracle: fields hand-read from the literal input.
        """
        result = isoparse('2016-10-01T14:30')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14
        assert result.minute == 30

    def test_iso8601_datetime_compact_hour(self):
        """Test ISO datetime compact with hour: 20161001T14.

        Mutation: a compact date before T split at the wrong offsets.
        Oracle: fields hand-read from the literal input.
        """
        result = isoparse('20161001T14')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14

    def test_iso8601_datetime_compact_hour_minute(self):
        """Test ISO datetime compact: 20161001T1430.

        Mutation: a 4-digit compact time read as a single hour field.
        Oracle: fields hand-read from the literal input.
        """
        result = isoparse('20161001T1430')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14
        assert result.minute == 30

    def test_iso8601_datetime_compact_with_tz(self):
        """Test ISO datetime compact with tz: 20161001T1430+0530.

        Mutation: a compact offset read as part of the compact time.
        Oracle: fields hand-read from the input. +0530 is 19800 s.
        """
        result = isoparse('20161001T1430+0530')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 14
        assert result.minute == 30
        assert result.tzoffset == 19800

    def test_iso8601_datetime_full_precision(self):
        """Test ISO datetime full precision: 2008-09-03T20:56:35.450686+01.

        Mutation: an hour-only offset after a fraction read as more
            fraction digits.
        Oracle: fields hand-read from the input. +01 is 3600 s.
        """
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
    """Test ISO 8601 week number formats (YYYY-Www).
    """

    @pytest.mark.parametrize(
        ('text', 'year', 'month', 'day'),
        [
            ('2012-W05', 2012, 1, 30),
            ('2012W05', 2012, 1, 30),
            ('2015W53', 2015, 12, 28),
            ('2012-W05-5', 2012, 2, 3),
            ('2012W055', 2012, 2, 3),
            ('2009-W53-7', 2010, 1, 3),
            ('2009-W01-1', 2008, 12, 29),
            ('2026W36', 2026, 8, 31),
            ])
    def test_iso8601_week_number(self, text, year, month, day):
        """Test week dates, with and without weekday, across year ends.

        Mutation: week 1 taken as the week of January 1 in place of the
            week holding the first Thursday, or the weekday counted from 0.
        Oracle: date.fromisocalendar() on each year, week and weekday.
            2026W36 is pendulum bug #916.
        """
        result = isoparse(text)
        assert result.year == year
        assert result.month == month
        assert result.day == day

    def test_iso8601_week_number_with_time(self):
        """Test ISO week with time: 2012-W05T09.

        Mutation: a time part after a week date dropped.
        Oracle: date.fromisocalendar(2012, 5, 1), hour from the input.
        """
        result = isoparse('2012-W05T09')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 30
        assert result.hour == 9

    def test_iso8601_week_number_with_time_compact(self):
        """Test ISO week with time compact: 2012W05T09.

        Mutation: a time part after a compact week date dropped.
        Oracle: date.fromisocalendar(2012, 5, 1), hour from the input.
        """
        result = isoparse('2012W05T09')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 30
        assert result.hour == 9


class TestPendulumISO8601Ordinal:
    """Test ISO 8601 ordinal date formats (YYYY-DDD).
    """

    def test_iso8601_ordinal(self):
        """Test ISO ordinal: 2012-007.

        Mutation: a 3-digit ordinal read as month and day digits.
        Oracle: day 7 of the year is January 7.
        """
        result = isoparse('2012-007')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 7

    def test_iso8601_ordinal_compact(self):
        """Test ISO ordinal compact: 2012007.

        Mutation: a 7-digit run rejected or split as YYYYMMD.
        Oracle: day 7 of the year is January 7.
        """
        result = isoparse('2012007')
        assert result.year == 2012
        assert result.month == 1
        assert result.day == 7


class TestPendulumISO8601Time:
    """Test ISO 8601 time-only formats.
    """

    def test_iso8601_time_colon(self):
        """Test ISO time: 20:12:05.

        Mutation: the colon-split time fields assigned in the wrong order.
        Oracle: fields hand-read from the literal input.
        """
        result = parse('20:12:05', fuzzy=True)
        assert result.hour == 20
        assert result.minute == 12
        assert result.second == 5

    def test_iso8601_time_microseconds(self):
        """Test ISO time with microseconds: 20:12:05.123456.

        Mutation: the fraction dropped or scaled as milliseconds.
        Oracle: fields hand-read from the literal input.
        """
        result = parse('20:12:05.123456', fuzzy=True)
        assert result.hour == 20
        assert result.minute == 12
        assert result.second == 5
        assert result.microsecond == 123456


class TestPendulumEdgeCases:
    """Test pendulum edge cases.
    """

    def test_single_digit_day(self):
        """Test single digit day: 2013-11-1.

        Mutation: a 1-digit trailing day field rejected.
        Oracle: fields hand-read from the literal input.
        """
        result = parse('2013-11-1', fuzzy=True)
        assert result.year == 2013
        assert result.month == 11
        assert result.day == 1

    @pytest.mark.xfail(reason='Pendulum interprets 10-01-01 as YY-MM-DD, dateutil as MM-DD-YY')
    def test_two_digit_year_10(self):
        """Test two digit year: 10-01-01.

        Mutation: none while xfail. Pendulum and dateutil disagree.
        Oracle: pendulum's YY-MM-DD reading.
        """
        result = parse('10-01-01', fuzzy=True)
        assert result.year == 2010
        assert result.month == 1
        assert result.day == 1

    @pytest.mark.xfail(reason='Pendulum interprets 31-01-01 as YY-MM-DD, dateutil as DD-MM-YY')
    def test_two_digit_year_31(self):
        """Test two digit year: 31-01-01.

        Mutation: none while xfail. Pendulum and dateutil disagree.
        Oracle: pendulum's YY-MM-DD reading.
        """
        result = parse('31-01-01', fuzzy=True)
        assert result.year == 2031
        assert result.month == 1
        assert result.day == 1

    def test_two_digit_year_32(self):
        """Test two digit year: 32-01-01.

        Mutation: a leading field above 31 read as a day, not the year.
        Oracle: 32 cannot be a day or month, so it is the year 2032.
        """
        result = parse('32-01-01', fuzzy=True)
        assert result.year == 2032
        assert result.month == 1
        assert result.day == 1


class TestPendulumStrict:
    """Test strict vs non-strict parsing.
    """

    def test_non_strict_format(self):
        """Test non-strict format: 4 Aug 2015 - 11:20 PM.

        Mutation: a dash before the time read as a negative offset, or
            PM not applied.
        Oracle: fields hand-read from the input. 11 PM is hour 23.
        """
        result = parse('4 Aug 2015 - 11:20 PM', fuzzy=True)
        assert result.year == 2015
        assert result.month == 8
        assert result.day == 4
        assert result.hour == 23
        assert result.minute == 20


class TestPendulumExifEdgeCase:
    """Test EXIF date format edge case.
    """

    @pytest.mark.xfail(reason='EXIF format (colon date separators) is pendulum-specific, not supported by dateutil')
    def test_exif_edge_case(self):
        """Test EXIF format: 2016:12:26 15:45:28.

        Mutation: none while xfail. The format is unsupported.
        Oracle: fields hand-read from the literal input.
        """
        result = parse('2016:12:26 15:45:28', fuzzy=True)
        assert result.year == 2016
        assert result.month == 12
        assert result.day == 26
        assert result.hour == 15
        assert result.minute == 45
        assert result.second == 28


class TestPendulumTimezones:
    """Test timezone parsing.
    """

    def test_utc_z(self):
        """Test UTC with Z.

        Mutation: a trailing Z left unread.
        Oracle: Z is UTC at offset 0, per ISO 8601.
        """
        result = isoparse('2016-10-06T12:34:56Z')
        assert result.year == 2016
        assert result.month == 10
        assert result.day == 6
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56
        assert result.tzoffset == 0

    @pytest.mark.parametrize(
        ('text', 'tzoffset'),
        [
            ('2016-10-06T12:34:56-08:00', -28800),
            ('2016-10-06T12:34:56+05', 18000),
            ('2016-10-06T12:34:56+0530', 19800),
            ])
    def test_offsets(self, text, tzoffset):
        """Test negative, hour-only and compact offsets.

        Mutation: the offset sign flipped, or an hour-only or compact
            offset rejected.
        Oracle: hand-computed offsets in seconds.
        """
        result = isoparse(text)
        assert result.tzoffset == tzoffset
