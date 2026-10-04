"""Basic parser tests - ported from dateutil.

These tests verify that the Rust parser matches dateutil's behavior
for standard date/time formats.
"""

import pytest

from opendate._opendate import Parser, parse


class TestParserBasicFormats:
    """Test basic date/time format parsing.
    """

    def test_parse_iso_datetime(self):
        """Test ISO format YYYY-MM-DDTHH:MM:SS.

        Mutation: the T separator not split, dropping the time fields.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_parse_iso_datetime_with_z(self):
        """Test ISO format with Z timezone.

        Mutation: a trailing Z left unread or named other than 'UTC'.
        Oracle: Z is UTC at offset 0, per ISO 8601.
        """
        r = parse('2024-01-15T10:30:45Z')
        assert r.year == 2024
        assert r.hour == 10
        assert r.tzoffset == 0
        assert r.tzname == 'UTC'

    def test_parse_us_date(self):
        """Test US format MM/DD/YYYY.

        Mutation: month and day swapped when dayfirst is off.
        Oracle: 15 cannot be a month, so 01/15 reads as January 15.
        """
        r = parse('01/15/2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_european_date_dayfirst(self):
        """Test European format DD/MM/YYYY with dayfirst=True.

        Mutation: Parser drops its dayfirst flag.
        Oracle: 15 cannot be a month, so 15/01 reads as January 15.
        """
        parser = Parser(dayfirst=True, yearfirst=False)
        r = parser.parse('15/01/2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_compact_date(self):
        """Test compact format YYYYMMDD.

        Mutation: an 8-digit run split at the wrong offsets.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('20240115')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_compact_datetime(self):
        """Test compact format YYYYMMDDHHMMSS.

        Mutation: a 14-digit run split at the wrong offsets.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('20240115103045')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestParserNamedMonths:
    """Test parsing with named months.
    """

    def test_parse_month_name_first(self):
        """Test format: January 15, 2024.

        Mutation: a leading month name not mapped to its number.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('January 15, 2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_month_abbrev_first(self):
        """Test format: Jan 15, 2024.

        Mutation: a three-letter month abbreviation not recognized.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('Jan 15, 2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_day_month_year(self):
        """Test format: 15-Jan-2024.

        Mutation: a dash-joined month name split as a numeric field.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('15-Jan-2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_day_month_name_year(self):
        """Test format: 15 January 2024.

        Mutation: a day before the month name taken as the year.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('15 January 2024', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    @pytest.mark.parametrize(
        ('name', 'num'),
        [
            ('January', 1),
            ('February', 2),
            ('March', 3),
            ('April', 4),
            ('May', 5),
            ('June', 6),
            ('July', 7),
            ('August', 8),
            ('September', 9),
            ('October', 10),
            ('November', 11),
            ('December', 12),
            ('Jan', 1),
            ('Feb', 2),
            ('Mar', 3),
            ('Apr', 4),
            ('Jun', 6),
            ('Jul', 7),
            ('Aug', 8),
            ('Sep', 9),
            ('Oct', 10),
            ('Nov', 11),
            ('Dec', 12),
            ])
    def test_parse_month_names(self, name, num):
        """Test every full month name and abbreviation.

        Mutation: an off-by-one or missing entry in the month table.
        Oracle: calendar order of the months.
        """
        r = parse(f'{name} 15, 2024')
        assert r.month == num


class TestParserTimeFormats:
    """Test time format parsing.
    """

    def test_parse_time_hms(self):
        """Test HH:MM:SS format.

        Mutation: the colon-split time fields assigned in the wrong order.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('10:30:45')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_parse_time_hm(self):
        """Test HH:MM format.

        Mutation: a two-field time read as minute and second.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('10:30')
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_time_with_microseconds(self):
        """Test time with microseconds.

        Mutation: the fraction dropped or scaled as milliseconds.
        Oracle: .123456 s is 123456 microseconds.
        """
        r = parse('10:30:45.123456')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45
        assert r.microsecond == 123456

    def test_parse_hms_labels(self):
        """Test 2h30m45s format.

        Mutation: the h, m or s label bound to the wrong field.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('2h30m45s')
        assert r.hour == 2
        assert r.minute == 30
        assert r.second == 45


class TestParserTimezones:
    """Test timezone parsing.
    """

    @pytest.mark.parametrize(
        ('text', 'tzname'),
        [
            ('2024-01-15 10:30:00 UTC', 'UTC'),
            ('2024-01-15 10:30:00 GMT', 'GMT'),
            ('2024-01-15T10:30:00Z', 'UTC'),
            ])
    def test_parse_utc_names(self, text, tzname):
        """Test UTC, GMT and Z each give offset 0 under the expected name.

        Mutation: GMT renamed to UTC, or a UTC name left without offset 0.
        Oracle: UTC, GMT and Z all sit at offset 0. Z takes the name 'UTC'.
        """
        r = parse(text)
        assert r.tzoffset == 0
        assert r.tzname == tzname

    @pytest.mark.parametrize(
        ('text', 'tzoffset'),
        [
            ('2024-01-15 10:30:00+05:30', 5 * 3600 + 30 * 60),
            ('2024-01-15 10:30:00-08:00', -8 * 3600),
            ('2024-01-15 10:30:00+0530', 5 * 3600 + 30 * 60),
            ('2024-01-15 10:30:00 GMT+3', -3 * 3600),
            ('2024-01-15 10:30:00 GMT-5', 5 * 3600),
            ])
    def test_parse_offsets(self, text, tzoffset):
        """Test numeric offsets, and the sign reversal of GMT+N and GMT-N.

        Mutation: the offset sign flipped, minutes dropped, or GMT+3 read
            as 3 hours ahead.
        Oracle: hand-computed seconds. dateutil reads GMT+3 as 3 hours
            behind GMT.
        """
        r = parse(text)
        assert r.tzoffset == tzoffset


class TestParserWeekdays:
    """Test weekday parsing.
    """

    def test_parse_weekday(self):
        """Test weekday name in date.

        Mutation: a leading weekday name consumed as the month or day.
        Oracle: Monday is weekday 0. Date fields hand-read from the input.
        """
        r = parse('Monday, January 15, 2024', fuzzy=True)
        assert r.weekday == 0
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    @pytest.mark.parametrize(
        ('name', 'num'),
        [
            ('Monday', 0),
            ('Tuesday', 1),
            ('Wednesday', 2),
            ('Thursday', 3),
            ('Friday', 4),
            ('Saturday', 5),
            ('Sunday', 6),
            ('Mon', 0),
            ('Tue', 1),
            ('Wed', 2),
            ('Thu', 3),
            ('Fri', 4),
            ('Sat', 5),
            ('Sun', 6),
            ])
    def test_parse_weekday_names(self, name, num):
        """Test every full weekday name and abbreviation.

        Mutation: weekdays numbered from Sunday or from 1.
        Oracle: Python's weekday() numbering, Monday 0 to Sunday 6.
        """
        r = parse(f'{name}, January 15, 2024', fuzzy=True)
        assert r.weekday == num


class TestParserTwoDigitYears:
    """Test two-digit year parsing.
    """

    def test_parse_two_digit_year_20s(self):
        """Test two-digit year in 20s.

        Mutation: a two-digit year left as year 24.
        Oracle: 24 falls within 50 years of the current year, so 2024.
        """
        r = parse('01/15/24')
        assert r.year == 2024

    def test_parse_two_digit_year_90s(self):
        """Test two-digit year in 90s (should be 1990s).

        Mutation: every two-digit year mapped into the 2000s.
        Oracle: 2090 lies over 50 years ahead, so the century before.
        """
        r = parse('01/15/90')
        assert r.year == 1990

    def test_parse_two_digit_year_50(self):
        """Test boundary two-digit year 50.

        Mutation: year 50 left as year 50 at the window boundary.
        Oracle: the century window either side of the current year.
        """
        r = parse('01/15/50')
        assert 1950 <= r.year <= 2050
