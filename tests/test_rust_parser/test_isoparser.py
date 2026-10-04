"""ISO 8601 parser tests - ported from dateutil test_isoparser.py.

These tests verify comprehensive ISO 8601 date/time parsing.
"""

import pytest

from opendate._opendate import IsoParser, isoparse


class TestIsoparserDates:
    """Test ISO 8601 date parsing.
    """

    def test_iso_date_yyyy(self):
        """Test year only: 2024.

        Mutation: a lone 4-digit year rejected as an incomplete date.
        Oracle: the literal input.
        """
        r = isoparse('2024')
        assert r.year == 2024

    def test_iso_date_yyyy_mm(self):
        """Test year-month: 2024-01.

        Mutation: the 2-digit field after the year read as a day.
        Oracle: fields hand-read from the literal input.
        """
        r = isoparse('2024-01')
        assert r.year == 2024
        assert r.month == 1

    def test_iso_date_yyyy_mm_dd(self):
        """Test full date: 2024-01-15.

        Mutation: month and day fields swapped.
        Oracle: fields hand-read from the literal input.
        """
        r = isoparse('2024-01-15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_iso_date_compact_yyyymmdd(self):
        """Test compact date: 20240115.

        Mutation: an 8-digit run split at the wrong offsets.
        Oracle: fields hand-read from the literal input.
        """
        r = isoparse('20240115')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15


class TestIsoparserDatetimes:
    """Test ISO 8601 datetime parsing.
    """

    def test_iso_datetime_t_separator(self):
        """Test datetime with T: 2024-01-15T10:30:45.

        Mutation: the T separator not split, dropping the time fields.
        Oracle: fields hand-read from the literal input.
        """
        r = isoparse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_iso_datetime_hour_only(self):
        """Test datetime with hour only: 2024-01-15T10.

        Mutation: a time part with only the hour rejected.
        Oracle: fields hand-read from the literal input.
        """
        r = isoparse('2024-01-15T10')
        assert r.year == 2024
        assert r.hour == 10

    def test_iso_datetime_hour_minute(self):
        """Test datetime with hour:minute: 2024-01-15T10:30.

        Mutation: a time part without seconds rejected.
        Oracle: fields hand-read from the literal input.
        """
        r = isoparse('2024-01-15T10:30')
        assert r.year == 2024
        assert r.hour == 10
        assert r.minute == 30

    def test_iso_datetime_compact(self):
        """Test compact datetime: 20240115T103045.

        Mutation: a 6-digit compact time split at the wrong offsets.
        Oracle: fields hand-read from the literal input.
        """
        r = isoparse('20240115T103045')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestIsoparserTimes:
    """Test ISO 8601 time parsing.
    """

    def test_iso_time_hh(self):
        """Test hour only: 10.

        Mutation: parse_isotime demands at least hour and minute.
        Oracle: the literal input.
        """
        parser = IsoParser()
        r = parser.parse_isotime('10')
        assert r.hour == 10

    def test_iso_time_hhmm(self):
        """Test hour:minute: 10:30.

        Mutation: hour and minute fields swapped.
        Oracle: fields hand-read from the literal input.
        """
        parser = IsoParser()
        r = parser.parse_isotime('10:30')
        assert r.hour == 10
        assert r.minute == 30

    def test_iso_time_hhmmss(self):
        """Test hour:minute:second: 10:30:45.

        Mutation: the third colon field dropped or bound to the wrong slot.
        Oracle: fields hand-read from the literal input.
        """
        parser = IsoParser()
        r = parser.parse_isotime('10:30:45')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_iso_time_compact_hhmm(self):
        """Test compact time: 1030.

        Mutation: a 4-digit compact time read as a single hour field.
        Oracle: fields hand-read from the literal input.
        """
        parser = IsoParser()
        r = parser.parse_isotime('1030')
        assert r.hour == 10
        assert r.minute == 30

    def test_iso_time_compact_hhmmss(self):
        """Test compact time: 103045.

        Mutation: a 6-digit compact time split at the wrong offsets.
        Oracle: fields hand-read from the literal input.
        """
        parser = IsoParser()
        r = parser.parse_isotime('103045')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestIsoparserMicroseconds:
    """Test ISO 8601 microsecond parsing.
    """

    @pytest.mark.parametrize(
        ('text', 'microsecond'),
        [
            ('2024-01-15T10:30:45.123456', 123456),
            ('2024-01-15T10:30:45.123', 123000),
            ('2024-01-15T10:30:45.1', 100000),
            ('2024-01-15T10:30:45,123456', 123456),
            ('2024-01-15T10:30:45.123456789', 123456),
            ])
    def test_iso_microseconds(self, text, microsecond):
        """Test 6-, 3-, 1- and 9-digit fractions, and a comma decimal mark.

        Mutation: a short fraction read as a whole count (.1 as 1 us), a
            9-digit fraction rounded or rejected, or the comma rejected.
        Oracle: hand-scaled fractions. Digits past the sixth truncate.
        """
        r = isoparse(text)
        assert r.microsecond == microsecond


class TestIsoparserTimezones:
    """Test ISO 8601 timezone parsing.
    """

    def test_iso_tz_z(self):
        """Test Z (UTC): 2024-01-15T10:30:45Z.

        Mutation: a trailing Z left unread or named other than 'UTC'.
        Oracle: Z is UTC at offset 0, per ISO 8601.
        """
        r = isoparse('2024-01-15T10:30:45Z')
        assert r.tzoffset == 0
        assert r.tzname == 'UTC'

    @pytest.mark.parametrize(
        ('text', 'tzoffset'),
        [
            ('2024-01-15T10:30:45+05:30', 5 * 3600 + 30 * 60),
            ('2024-01-15T10:30:45-08:00', -8 * 3600),
            ('2024-01-15T10:30:45+0530', 5 * 3600 + 30 * 60),
            ('2024-01-15T10:30:45-0800', -8 * 3600),
            ('2024-01-15T10:30:45+05', 5 * 3600),
            ('2024-01-15T10:30:45-08', -8 * 3600),
            ('2024-01-15T10:30:45+00:00', 0),
            ('2024-01-15T10:30:45-00:00', 0),
            ])
    def test_iso_tz_offsets(self, text, tzoffset):
        """Test extended, compact and hour-only offsets of either sign.

        Mutation: the offset sign flipped, minutes dropped, or a compact
            or hour-only offset rejected.
        Oracle: hand-computed offsets in seconds. -00:00 equals +00:00.
        """
        r = isoparse(text)
        assert r.tzoffset == tzoffset


class TestIsoparserClass:
    """Test IsoParser class.
    """

    def test_isoparser_default(self):
        """Test default IsoParser.

        Mutation: the default separator set to anything but T.
        Oracle: fields hand-read from the literal input.
        """
        parser = IsoParser()
        r = parser.isoparse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.hour == 10

    def test_isoparser_custom_sep(self):
        """Test IsoParser with custom separator.

        Mutation: IsoParser drops its sep argument and splits only on T.
        Oracle: fields hand-read from the literal input.
        """
        parser = IsoParser(sep=' ')
        r = parser.isoparse('2024-01-15 10:30:45')
        assert r.year == 2024
        assert r.hour == 10

    def test_isoparser_parse_isodate(self):
        """Test parse_isodate method.

        Mutation: parse_isodate bound to the time parser.
        Oracle: fields hand-read from the literal input.
        """
        parser = IsoParser()
        r = parser.parse_isodate('2024-01-15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15


class TestIsoparserEdgeCases:
    """Test ISO parser edge cases.
    """

    def test_iso_midnight(self):
        """Test midnight: 00:00:00.

        Mutation: a zero field treated as missing and returned as None.
        Oracle: the literal input.
        """
        r = isoparse('2024-01-15T00:00:00')
        assert r.hour == 0
        assert r.minute == 0
        assert r.second == 0

    def test_iso_end_of_day(self):
        """Test end of day: 23:59:59.

        Mutation: an off-by-one upper bound that rejects 23 or 59.
        Oracle: the largest valid hour, minute and second.
        """
        r = isoparse('2024-01-15T23:59:59')
        assert r.hour == 23
        assert r.minute == 59
        assert r.second == 59

    def test_iso_leap_year_feb_29(self):
        """Test Feb 29 in leap year.

        Mutation: the leap-year rule dropped, so Feb 29 is rejected.
        Oracle: 2024 is divisible by 4 and not by 100, so a leap year.
        """
        r = isoparse('2024-02-29')
        assert r.year == 2024
        assert r.month == 2
        assert r.day == 29

    def test_iso_min_year(self):
        """Test minimum year: 0001.

        Mutation: a year below 1000 rejected or read as a 2-digit year.
        Oracle: the literal input.
        """
        r = isoparse('0001-01-01')
        assert r.year == 1

    def test_iso_max_common_year(self):
        """Test year 9999.

        Mutation: an off-by-one upper bound that rejects year 9999.
        Oracle: 9999-12-31 is the last date datetime accepts.
        """
        r = isoparse('9999-12-31')
        assert r.year == 9999
        assert r.month == 12
        assert r.day == 31

    def test_iso_with_microseconds_and_tz(self):
        """Test full ISO with microseconds and timezone.

        Mutation: the offset sign read as part of the fraction.
        Oracle: fields hand-read from the literal input.
        """
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
    """Test various ISO format variants.
    """

    def test_all_months(self):
        """Test parsing all months.

        Mutation: an off-by-one or upper bound that rejects month 12.
        Oracle: the loop month written into the input.
        """
        for month in range(1, 13):
            date_str = f'2024-{month:02d}-15'
            r = isoparse(date_str)
            assert r.month == month, f'Failed for month {month}'

    def test_all_days(self):
        """Test parsing various days of month.

        Mutation: an upper bound that rejects day 31 in a 31-day month.
        Oracle: the loop day written into the input.
        """
        for day in [1, 10, 15, 20, 28, 30, 31]:
            date_str = f'2024-01-{day:02d}'
            r = isoparse(date_str)
            assert r.day == day, f'Failed for day {day}'

    def test_various_hours(self):
        """Test parsing various hours.

        Mutation: hour 0 treated as missing, or an upper bound below 23.
        Oracle: the loop hour written into the input.
        """
        for hour in [0, 6, 12, 18, 23]:
            time_str = f'2024-01-15T{hour:02d}:30:45'
            r = isoparse(time_str)
            assert r.hour == hour, f'Failed for hour {hour}'

    def test_various_timezones(self):
        """Test various timezone offsets.

        Mutation: the offset sign flipped, or a bound below +-12 hours.
        Oracle: hand-computed offsets in seconds.
        """
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
    """Test that invalid formats are rejected.
    """

    def test_time_trailing_digit(self):
        """Test that trailing digit is rejected: 09301 (5 digits).

        Mutation: parse_isotime stops after HHMM and ignores the rest.
        Oracle: ISO 8601 has no 5-digit time form.
        """
        parser = IsoParser()
        with pytest.raises(Exception):
            parser.parse_isotime('09301')

    def test_time_trailing_text(self):
        """Test that trailing text is rejected: 14:30extra.

        Mutation: parse_isotime ignores text after the last field.
        Oracle: ISO 8601 allows no trailing letters.
        """
        parser = IsoParser()
        with pytest.raises(Exception):
            parser.parse_isotime('14:30extra')

    def test_time_ampm_suffix(self):
        """Test that AM/PM suffixes are rejected (ISO doesn't support).

        Mutation: the free-form parser's am/pm handling reused in
            parse_isotime.
        Oracle: ISO 8601 has only the 24-hour clock.
        """
        parser = IsoParser()
        with pytest.raises(Exception):
            parser.parse_isotime('0930 pm')
        with pytest.raises(Exception):
            parser.parse_isotime('09:30 pm')
        with pytest.raises(Exception):
            parser.parse_isotime('09:30am')

    def test_time_microseconds_trailing_text(self):
        """Test that trailing text after microseconds is rejected.

        Mutation: the fraction reader stops at the first letter and
            accepts.
        Oracle: ISO 8601 allows no trailing letters.
        """
        parser = IsoParser()
        with pytest.raises(Exception):
            parser.parse_isotime('14:30:45.123extra')

    def test_datetime_trailing_text(self):
        """Test that datetime with trailing text is rejected.

        Mutation: isoparse ignores text after the time part.
        Oracle: ISO 8601 allows no trailing letters.
        """
        with pytest.raises(Exception):
            isoparse('2024-01-15T09:30extra')
        with pytest.raises(Exception):
            isoparse('2024-01-15T093015X')

    def test_time_trailing_whitespace_allowed(self):
        """Test that trailing whitespace IS allowed.

        Mutation: the trailing-text check rejects whitespace too.
        Oracle: fields hand-read from the input before the whitespace.
        """
        parser = IsoParser()
        r = parser.parse_isotime('14:30 ')
        assert r.hour == 14
        assert r.minute == 30

        r = parser.parse_isotime('14:30:45\t')
        assert r.hour == 14
        assert r.minute == 30
        assert r.second == 45
