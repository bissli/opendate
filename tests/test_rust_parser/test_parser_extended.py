"""Extended parser tests - ported from dateutil test_parser.py.

These tests cover more complex parsing scenarios and edge cases.
"""

import pytest

from date._opendate import Parser, parse


class TestParserMoreFormats:
    """Test additional date/time formats from dateutil."""

    def test_parse_date_with_spaces(self):
        """Test date with spaces: Jan 15 2024."""
        r = parse('Jan 15 2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_date_dash_separator(self):
        """Test date with dash separator: 15-Jan-2024."""
        r = parse('15-Jan-2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_date_dot_separator(self):
        """Test date with dot separator: 15.01.2024."""
        parser = Parser(dayfirst=True)
        r = parser.parse('15.01.2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_date_year_first(self):
        """Test date with year first: 2024/01/15."""
        r = parse('2024/01/15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_datetime_with_comma(self):
        """Test datetime: Jan 15, 2024, 10:30."""
        r = parse('Jan 15, 2024, 10:30', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_datetime_at(self):
        """Test datetime with 'at': Jan 15, 2024 at 10:30."""
        r = parse('Jan 15, 2024 at 10:30', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_datetime_on(self):
        """Test datetime with 'on': 10:30 on Jan 15, 2024."""
        r = parse('10:30 on Jan 15, 2024', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_datetime_t_separator(self):
        """Test ISO datetime with T separator."""
        r = parse('2024-01-15T10:30:45')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_parse_datetime_space_separator(self):
        """Test datetime with space separator."""
        r = parse('2024-01-15 10:30:45')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestParserMicroseconds:
    """Test microsecond parsing."""

    def test_parse_microseconds_6_digits(self):
        """Test 6-digit microseconds."""
        r = parse('2024-01-15T10:30:45.123456')
        assert r.microsecond == 123456

    def test_parse_microseconds_3_digits(self):
        """Test 3-digit milliseconds (converted to microseconds)."""
        r = parse('2024-01-15T10:30:45.123')
        assert r.microsecond == 123000

    def test_parse_microseconds_1_digit(self):
        """Test 1-digit fractional second."""
        r = parse('2024-01-15T10:30:45.1')
        assert r.microsecond == 100000

    def test_parse_microseconds_comma_separator(self):
        """Test comma as decimal separator."""
        r = parse('2024-01-15T10:30:45,123456')
        assert r.microsecond == 123456


class TestParserTimezoneOffsets:
    """Test timezone offset parsing."""

    def test_parse_offset_plus_hhmm(self):
        """Test +HH:MM offset."""
        r = parse('2024-01-15T10:30:00+05:30')
        assert r.tzoffset == 5 * 3600 + 30 * 60

    def test_parse_offset_minus_hhmm(self):
        """Test -HH:MM offset."""
        r = parse('2024-01-15T10:30:00-05:30')
        assert r.tzoffset == -(5 * 3600 + 30 * 60)

    def test_parse_offset_compact_plus(self):
        """Test +HHMM offset (no colon)."""
        r = parse('2024-01-15T10:30:00+0530')
        assert r.tzoffset == 5 * 3600 + 30 * 60

    def test_parse_offset_compact_minus(self):
        """Test -HHMM offset (no colon)."""
        r = parse('2024-01-15T10:30:00-0800')
        assert r.tzoffset == -8 * 3600

    def test_parse_offset_hour_only(self):
        """Test +HH offset."""
        r = parse('2024-01-15T10:30:00+05')
        assert r.tzoffset == 5 * 3600

    def test_parse_est(self):
        """Test EST timezone name (name captured, offset requires tzinfos)."""
        r = parse('2024-01-15 10:30:00 EST')
        assert r.tzname == 'EST'
        # Note: Named timezones don't have default offsets (matches dateutil behavior)
        # Offsets require tzinfos parameter

    def test_parse_pst(self):
        """Test PST timezone name (name captured, offset requires tzinfos)."""
        r = parse('2024-01-15 10:30:00 PST')
        assert r.tzname == 'PST'
        # Note: Named timezones don't have default offsets (matches dateutil behavior)

    def test_parse_cet(self):
        """Test CET timezone name (name captured, offset requires tzinfos)."""
        r = parse('2024-01-15 10:30:00 CET')
        assert r.tzname == 'CET'
        # Note: Named timezones don't have default offsets (matches dateutil behavior)


class TestParserAMPM:
    """Test AM/PM parsing."""

    def test_parse_lowercase_am(self):
        """Test lowercase am."""
        r = parse('10:30 am')
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_lowercase_pm(self):
        """Test lowercase pm."""
        r = parse('2:30 pm')
        assert r.hour == 14
        assert r.minute == 30

    def test_parse_uppercase_am(self):
        """Test uppercase AM."""
        r = parse('10:30 AM')
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_uppercase_pm(self):
        """Test uppercase PM."""
        r = parse('2:30 PM')
        assert r.hour == 14
        assert r.minute == 30

    def test_parse_period_am(self):
        """Test a.m. format."""
        r = parse('10:30 a.m.')
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_period_pm(self):
        """Test p.m. format."""
        r = parse('2:30 p.m.')
        assert r.hour == 14
        assert r.minute == 30

    def test_parse_12_am_midnight(self):
        """Test 12:00 AM is midnight."""
        r = parse('12:00 AM')
        assert r.hour == 0
        assert r.minute == 0

    def test_parse_12_pm_noon(self):
        """Test 12:00 PM is noon."""
        r = parse('12:00 PM')
        assert r.hour == 12
        assert r.minute == 0

    def test_parse_12_30_am(self):
        """Test 12:30 AM."""
        r = parse('12:30 AM')
        assert r.hour == 0
        assert r.minute == 30

    def test_parse_12_30_pm(self):
        """Test 12:30 PM."""
        r = parse('12:30 PM')
        assert r.hour == 12
        assert r.minute == 30


class TestParserDayFirst:
    """Test dayfirst option."""

    def test_dayfirst_false(self):
        """Test MM/DD/YYYY with dayfirst=False."""
        parser = Parser(dayfirst=False)
        r = parser.parse('01/15/2024')
        assert r.month == 1
        assert r.day == 15

    def test_dayfirst_true(self):
        """Test DD/MM/YYYY with dayfirst=True."""
        parser = Parser(dayfirst=True)
        r = parser.parse('15/01/2024')
        assert r.day == 15
        assert r.month == 1

    def test_dayfirst_ambiguous(self):
        """Test ambiguous date 05/06/2024."""
        # dayfirst=False (default) - MM/DD
        r1 = parse('05/06/2024')
        assert r1.month == 5
        assert r1.day == 6

        # dayfirst=True - DD/MM
        parser = Parser(dayfirst=True)
        r2 = parser.parse('05/06/2024')
        assert r2.day == 5
        assert r2.month == 6


class TestParserYearFirst:
    """Test yearfirst option."""

    def test_yearfirst_false(self):
        """Test MM/DD/YY with yearfirst=False."""
        parser = Parser(yearfirst=False)
        r = parser.parse('01/15/24')
        assert r.month == 1
        assert r.day == 15
        assert r.year == 2024

    def test_yearfirst_true(self):
        """Test YY/MM/DD with yearfirst=True."""
        parser = Parser(yearfirst=True)
        r = parser.parse('24/01/15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15


class TestParserSpecialFormats:
    """Test special format parsing."""

    def test_parse_ordinal_day(self):
        """Test ordinal day: January 15th, 2024."""
        r = parse('January 15th, 2024', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_ordinal_1st(self):
        """Test 1st ordinal."""
        r = parse('January 1st, 2024', fuzzy=True)
        assert r.day == 1

    def test_parse_ordinal_2nd(self):
        """Test 2nd ordinal."""
        r = parse('January 2nd, 2024', fuzzy=True)
        assert r.day == 2

    def test_parse_ordinal_3rd(self):
        """Test 3rd ordinal."""
        r = parse('January 3rd, 2024', fuzzy=True)
        assert r.day == 3

    def test_parse_year_month(self):
        """Test year-month only: 2024-01."""
        r = parse('2024-01')
        assert r.year == 2024
        assert r.month == 1

    def test_parse_month_year(self):
        """Test month year: January 2024."""
        r = parse('January 2024')
        assert r.year == 2024
        assert r.month == 1

    def test_parse_year_only(self):
        """Test year only: 2024."""
        r = parse('2024')
        assert r.year == 2024


class TestParserFuzzyMode:
    """Test fuzzy parsing mode."""

    def test_fuzzy_leading_text(self):
        """Test fuzzy with leading text."""
        r = parse('Today is 2024-01-15', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_fuzzy_trailing_text(self):
        """Test fuzzy with trailing text."""
        r = parse('2024-01-15 was yesterday', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_fuzzy_surrounding_text(self):
        """Test fuzzy with surrounding text."""
        r = parse('The date 2024-01-15 is important', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_fuzzy_order_number(self):
        """Test fuzzy ignores order numbers."""
        r = parse('Order #12345 placed on 2024-01-15', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_fuzzy_with_tokens_returns_tuple(self):
        """Test fuzzy_with_tokens returns tuple."""
        parser = Parser()
        result = parser.parse('Today is 2024-01-15', fuzzy=True, fuzzy_with_tokens=True)
        assert isinstance(result, tuple)
        assert len(result) == 2
        r, tokens = result
        assert r.year == 2024
        assert isinstance(tokens, list)


class TestParserEdgeCases:
    """Test edge cases and special scenarios."""

    def test_parse_time_only(self):
        """Test parsing time only."""
        r = parse('10:30:45')
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45

    def test_parse_date_only(self):
        """Test parsing date only."""
        r = parse('2024-01-15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour is None
        assert r.minute is None

    def test_parse_month_name_case_insensitive(self):
        """Test month name is case insensitive."""
        r1 = parse('JANUARY 15, 2024')
        r2 = parse('january 15, 2024')
        r3 = parse('January 15, 2024')
        assert r1.month == r2.month == r3.month == 1

    def test_parse_weekday_case_insensitive(self):
        """Test weekday is case insensitive."""
        r1 = parse('MONDAY, January 15, 2024', fuzzy=True)
        r2 = parse('monday, January 15, 2024', fuzzy=True)
        assert r1.weekday == r2.weekday == 0

    def test_parse_yyyymmdd_compact(self):
        """Test compact YYYYMMDD."""
        r = parse('20240115')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_yyyymmddhhmmss_compact(self):
        """Test compact YYYYMMDDHHMMSS."""
        r = parse('20240115103045')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45
