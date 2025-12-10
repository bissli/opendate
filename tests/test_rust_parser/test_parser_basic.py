"""Basic parser tests - ported from dateutil.

These tests verify that the Rust parser matches dateutil's behavior
for standard date/time formats.
"""

import pytest

from opendate._opendate import IsoParser, Parser, isoparse, parse


class TestParserBasicFormats:
    """Test basic date/time format parsing."""

    def test_parse_iso_date(self):
        """Test ISO format YYYY-MM-DD."""
        r = parse('2024-01-15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_iso_datetime(self):
        """Test ISO format YYYY-MM-DDTHH:MM:SS."""
        r = parse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_parse_iso_datetime_with_z(self):
        """Test ISO format with Z timezone."""
        r = parse('2024-01-15T10:30:45Z')
        assert r.year == 2024
        assert r.hour == 10
        assert r.tzoffset == 0
        assert r.tzname == 'UTC'

    def test_parse_us_date(self):
        """Test US format MM/DD/YYYY."""
        r = parse('01/15/2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_european_date_dayfirst(self):
        """Test European format DD/MM/YYYY with dayfirst=True."""
        parser = Parser(dayfirst=True, yearfirst=False)
        r = parser.parse('15/01/2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_compact_date(self):
        """Test compact format YYYYMMDD."""
        r = parse('20240115')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_compact_datetime(self):
        """Test compact format YYYYMMDDHHMMSS."""
        r = parse('20240115103045')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestParserNamedMonths:
    """Test parsing with named months."""

    def test_parse_month_name_first(self):
        """Test format: January 15, 2024."""
        r = parse('January 15, 2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_month_abbrev_first(self):
        """Test format: Jan 15, 2024."""
        r = parse('Jan 15, 2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_day_month_year(self):
        """Test format: 15-Jan-2024."""
        r = parse('15-Jan-2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_day_month_name_year(self):
        """Test format: 15 January 2024."""
        r = parse('15 January 2024', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_all_months(self):
        """Test all month names."""
        months = [
            ('January', 1), ('February', 2), ('March', 3), ('April', 4),
            ('May', 5), ('June', 6), ('July', 7), ('August', 8),
            ('September', 9), ('October', 10), ('November', 11), ('December', 12)
        ]
        for name, num in months:
            r = parse(f'{name} 15, 2024')
            assert r.month == num, f'Failed for {name}'

    def test_parse_month_abbreviations(self):
        """Test month abbreviations."""
        months = [
            ('Jan', 1), ('Feb', 2), ('Mar', 3), ('Apr', 4),
            ('May', 5), ('Jun', 6), ('Jul', 7), ('Aug', 8),
            ('Sep', 9), ('Oct', 10), ('Nov', 11), ('Dec', 12)
        ]
        for abbrev, num in months:
            r = parse(f'{abbrev} 15, 2024')
            assert r.month == num, f'Failed for {abbrev}'


class TestParserTimeFormats:
    """Test time format parsing."""

    def test_parse_time_hms(self):
        """Test HH:MM:SS format."""
        r = parse('10:30:45')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_parse_time_hm(self):
        """Test HH:MM format."""
        r = parse('10:30')
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_time_with_microseconds(self):
        """Test time with microseconds."""
        r = parse('10:30:45.123456')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45
        assert r.microsecond == 123456

    def test_parse_time_am(self):
        """Test time with AM."""
        r = parse('10:30 AM')
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_time_pm(self):
        """Test time with PM."""
        r = parse('2:30 PM')
        assert r.hour == 14
        assert r.minute == 30

    def test_parse_12_pm(self):
        """Test 12 PM is noon."""
        r = parse('12:00 PM')
        assert r.hour == 12

    def test_parse_12_am(self):
        """Test 12 AM is midnight."""
        r = parse('12:00 AM')
        assert r.hour == 0

    def test_parse_hms_labels(self):
        """Test 2h30m45s format."""
        r = parse('2h30m45s')
        assert r.hour == 2
        assert r.minute == 30
        assert r.second == 45


class TestParserTimezones:
    """Test timezone parsing."""

    def test_parse_utc(self):
        """Test UTC timezone."""
        r = parse('2024-01-15 10:30:00 UTC')
        assert r.tzoffset == 0
        assert r.tzname == 'UTC'

    def test_parse_gmt(self):
        """Test GMT timezone."""
        r = parse('2024-01-15 10:30:00 GMT')
        assert r.tzoffset == 0
        assert r.tzname == 'GMT'

    def test_parse_z_timezone(self):
        """Test Z timezone (via ISO parser)."""
        r = parse('2024-01-15T10:30:00Z')
        assert r.tzoffset == 0
        assert r.tzname == 'UTC'

    def test_parse_positive_offset(self):
        """Test positive timezone offset."""
        r = parse('2024-01-15 10:30:00+05:30')
        assert r.tzoffset == 5 * 3600 + 30 * 60

    def test_parse_negative_offset(self):
        """Test negative timezone offset."""
        r = parse('2024-01-15 10:30:00-08:00')
        assert r.tzoffset == -8 * 3600

    def test_parse_compact_offset(self):
        """Test compact timezone offset."""
        r = parse('2024-01-15 10:30:00+0530')
        assert r.tzoffset == 5 * 3600 + 30 * 60

    def test_parse_gmt_plus_sign_reversal(self):
        """Test GMT+3 sign reversal (GMT+3 means -3 hours from GMT)."""
        r = parse('2024-01-15 10:30:00 GMT+3')
        assert r.tzoffset == -3 * 3600

    def test_parse_gmt_minus_sign_reversal(self):
        """Test GMT-5 sign reversal (GMT-5 means +5 hours from GMT)."""
        r = parse('2024-01-15 10:30:00 GMT-5')
        assert r.tzoffset == 5 * 3600


class TestParserWeekdays:
    """Test weekday parsing."""

    def test_parse_weekday(self):
        """Test weekday name in date."""
        r = parse('Monday, January 15, 2024', fuzzy=True)
        assert r.weekday == 0  # Monday = 0
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_all_weekdays(self):
        """Test all weekday names."""
        weekdays = [
            ('Monday', 0), ('Tuesday', 1), ('Wednesday', 2), ('Thursday', 3),
            ('Friday', 4), ('Saturday', 5), ('Sunday', 6)
        ]
        for name, num in weekdays:
            r = parse(f'{name}, January 15, 2024', fuzzy=True)
            assert r.weekday == num, f'Failed for {name}'

    def test_parse_weekday_abbreviations(self):
        """Test weekday abbreviations."""
        weekdays = [
            ('Mon', 0), ('Tue', 1), ('Wed', 2), ('Thu', 3),
            ('Fri', 4), ('Sat', 5), ('Sun', 6)
        ]
        for abbrev, num in weekdays:
            r = parse(f'{abbrev}, January 15, 2024', fuzzy=True)
            assert r.weekday == num, f'Failed for {abbrev}'


class TestParserTwoDigitYears:
    """Test two-digit year parsing."""

    def test_parse_two_digit_year_20s(self):
        """Test two-digit year in 20s."""
        r = parse('01/15/24')
        assert r.year == 2024

    def test_parse_two_digit_year_90s(self):
        """Test two-digit year in 90s (should be 1990s)."""
        r = parse('01/15/90')
        assert r.year == 1990

    def test_parse_two_digit_year_50(self):
        """Test boundary two-digit year 50."""
        r = parse('01/15/50')
        # Should be in the range [current_year - 50, current_year + 49]
        assert 1950 <= r.year <= 2050


class TestParserFuzzy:
    """Test fuzzy parsing."""

    def test_fuzzy_with_text(self):
        """Test fuzzy parsing with surrounding text."""
        r = parse('Today is 2024-01-15', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_fuzzy_with_numbers(self):
        """Test fuzzy parsing ignores non-date numbers."""
        r = parse('Order #12345 placed on 2024-01-15', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_fuzzy_with_tokens(self):
        """Test fuzzy_with_tokens returns skipped tokens."""
        parser = Parser()
        result, tokens = parser.parse('Today is 2024-01-15', fuzzy=True, fuzzy_with_tokens=True)
        assert result.year == 2024
        assert tokens is not None
        assert len(tokens) > 0


class TestIsoParser:
    """Test ISO 8601 parser."""

    def test_isoparse_date(self):
        """Test ISO date parsing."""
        r = isoparse('2024-01-15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_isoparse_datetime(self):
        """Test ISO datetime parsing."""
        r = isoparse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.hour == 10

    def test_isoparse_datetime_z(self):
        """Test ISO datetime with Z."""
        r = isoparse('2024-01-15T10:30:45Z')
        assert r.tzoffset == 0
        assert r.tzname == 'UTC'

    def test_isoparse_datetime_offset(self):
        """Test ISO datetime with offset."""
        r = isoparse('2024-01-15T10:30:45+05:30')
        assert r.tzoffset == 5 * 3600 + 30 * 60

    def test_isoparse_compact(self):
        """Test compact ISO format."""
        r = isoparse('20240115')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_isoparse_microseconds(self):
        """Test ISO with microseconds."""
        r = isoparse('2024-01-15T10:30:45.123456')
        assert r.microsecond == 123456

    def test_isoparser_class(self):
        """Test IsoParser class."""
        parser = IsoParser()
        r = parser.isoparse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.hour == 10

    def test_isoparser_with_separator(self):
        """Test IsoParser with custom separator."""
        parser = IsoParser(sep=' ')
        r = parser.isoparse('2024-01-15 10:30:45')
        assert r.year == 2024
        assert r.hour == 10
