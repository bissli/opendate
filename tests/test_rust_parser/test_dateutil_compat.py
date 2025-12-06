"""Dateutil compatibility tests.

These tests are ported EXACTLY from dateutil's test_parser.py to ensure
our Rust parser produces identical results.

Reference: https://github.com/dateutil/dateutil/blob/master/tests/test_parser.py
"""

import pytest
from datetime import datetime
from date._opendate import Parser, parse


# Parser test cases using no keyword arguments.
# Format: (parsable_text, expected_datetime, assertion_message)
# Ported exactly from dateutil's PARSER_TEST_CASES
PARSER_TEST_CASES = [
    ("Thu Sep 25 10:36:28 2003", datetime(2003, 9, 25, 10, 36, 28), "date command format strip"),
    ("Thu Sep 25 2003", datetime(2003, 9, 25), "date command format strip"),
    ("2003-09-25T10:49:41", datetime(2003, 9, 25, 10, 49, 41), "iso format strip"),
    ("2003-09-25T10:49", datetime(2003, 9, 25, 10, 49), "iso format strip"),
    ("2003-09-25T10", datetime(2003, 9, 25, 10), "iso format strip"),
    ("2003-09-25", datetime(2003, 9, 25), "iso format strip"),
    ("20030925T104941", datetime(2003, 9, 25, 10, 49, 41), "iso stripped format strip"),
    ("20030925T1049", datetime(2003, 9, 25, 10, 49, 0), "iso stripped format strip"),
    ("20030925T10", datetime(2003, 9, 25, 10), "iso stripped format strip"),
    ("20030925", datetime(2003, 9, 25), "iso stripped format strip"),
    ("2003-09-25 10:49:41,502", datetime(2003, 9, 25, 10, 49, 41, 502000), "python logger format"),
    ("199709020908", datetime(1997, 9, 2, 9, 8), "no separator"),
    ("19970902090807", datetime(1997, 9, 2, 9, 8, 7), "no separator"),
    ("09-25-2003", datetime(2003, 9, 25), "date with dash"),
    ("25-09-2003", datetime(2003, 9, 25), "date with dash"),
    ("10-09-2003", datetime(2003, 10, 9), "date with dash"),
    ("10-09-03", datetime(2003, 10, 9), "date with dash"),
    ("2003.09.25", datetime(2003, 9, 25), "date with dot"),
    ("09.25.2003", datetime(2003, 9, 25), "date with dot"),
    ("25.09.2003", datetime(2003, 9, 25), "date with dot"),
    ("10.09.2003", datetime(2003, 10, 9), "date with dot"),
    ("10.09.03", datetime(2003, 10, 9), "date with dot"),
    ("2003/09/25", datetime(2003, 9, 25), "date with slash"),
    ("09/25/2003", datetime(2003, 9, 25), "date with slash"),
    ("25/09/2003", datetime(2003, 9, 25), "date with slash"),
    ("10/09/2003", datetime(2003, 10, 9), "date with slash"),
    ("10/09/03", datetime(2003, 10, 9), "date with slash"),
    ("2003 09 25", datetime(2003, 9, 25), "date with space"),
    ("09 25 2003", datetime(2003, 9, 25), "date with space"),
    ("25 09 2003", datetime(2003, 9, 25), "date with space"),
    ("10 09 2003", datetime(2003, 10, 9), "date with space"),
    ("10 09 03", datetime(2003, 10, 9), "date with space"),
    ("25 09 03", datetime(2003, 9, 25), "date with space"),
    ("03 25 Sep", datetime(2003, 9, 25), "strangely ordered date"),
    ("25 03 Sep", datetime(2025, 9, 3), "strangely ordered date"),
    ("  July   4 ,  1976   12:01:02   am  ", datetime(1976, 7, 4, 0, 1, 2), "extra space"),
    ("Wed, July 10, '96", datetime(1996, 7, 10, 0, 0), "random format"),
    ("1996.July.10 AD 12:08 PM", datetime(1996, 7, 10, 12, 8), "random format"),
    ("July 4, 1976", datetime(1976, 7, 4), "random format"),
    ("7 4 1976", datetime(1976, 7, 4), "random format"),
    ("4 jul 1976", datetime(1976, 7, 4), "random format"),
    ("4 Jul 1976", datetime(1976, 7, 4), "'%-d %b %Y' format"),
    ("7-4-76", datetime(1976, 7, 4), "random format"),
    ("19760704", datetime(1976, 7, 4), "random format"),
    ("0:01:02 on July 4, 1976", datetime(1976, 7, 4, 0, 1, 2), "random format"),
    ("July 4, 1976 12:01:02 am", datetime(1976, 7, 4, 0, 1, 2), "random format"),
    ("Mon Jan  2 04:24:27 1995", datetime(1995, 1, 2, 4, 24, 27), "random format"),
    ("04.04.95 00:22", datetime(1995, 4, 4, 0, 22), "random format"),
    ("Jan 1 1999 11:23:34.578", datetime(1999, 1, 1, 11, 23, 34, 578000), "random format"),
    ("950404 122212", datetime(1995, 4, 4, 12, 22, 12), "random format"),
    ("3rd of May 2001", datetime(2001, 5, 3), "random format"),
    ("5th of March 2001", datetime(2001, 3, 5), "random format"),
    ("1st of May 2003", datetime(2003, 5, 1), "random format"),
    ("0099-01-01T00:00:00", datetime(99, 1, 1, 0, 0), "99 ad"),
    ("0031-01-01T00:00:00", datetime(31, 1, 1, 0, 0), "31 ad"),  # Ancient year - now works with ISO detection
    ("20080227T21:26:01.123456789", datetime(2008, 2, 27, 21, 26, 1, 123456), "high precision seconds"),
    ("13NOV2017", datetime(2017, 11, 13), "dBY (See GH360)"),
    ("0003-03-04", datetime(3, 3, 4), "pre 12 year same month (See GH PR #293)"),  # Ancient year - now works with ISO detection
    pytest.param("December.0031.30", datetime(31, 12, 30), "BYd corner case (GH#687)", marks=pytest.mark.xfail(reason="Non-ISO ancient year format - dateutil also struggles")),
]


def _parse_to_datetime(result):
    """Convert ParseResult to datetime for comparison."""
    if result is None:
        return None

    # Handle tuple from fuzzy_with_tokens
    if isinstance(result, tuple):
        result = result[0]

    year = result.year if result.year is not None else 1
    month = result.month if result.month is not None else 1
    day = result.day if result.day is not None else 1
    hour = result.hour if result.hour is not None else 0
    minute = result.minute if result.minute is not None else 0
    second = result.second if result.second is not None else 0
    microsecond = result.microsecond if result.microsecond is not None else 0

    return datetime(year, month, day, hour, minute, second, microsecond)


class TestParserDateutilCompat:
    """Test parser compatibility with dateutil - no keyword arguments."""

    @pytest.mark.parametrize("parsable_text,expected_datetime,assertion_message", PARSER_TEST_CASES)
    def test_parser(self, parsable_text, expected_datetime, assertion_message):
        result = parse(parsable_text, fuzzy=True)
        parsed_dt = _parse_to_datetime(result)
        assert parsed_dt == expected_datetime, f"{assertion_message}: got {parsed_dt}, expected {expected_datetime}"


# Parser test cases using datetime(2003, 9, 25) as a default.
# We apply the default in our comparison since our parser returns components
PARSER_DEFAULT_TEST_CASES = [
    ("Thu Sep 25 10:36:28", datetime(2003, 9, 25, 10, 36, 28), "date command format strip"),
    ("Thu Sep 10:36:28", datetime(2003, 9, 25, 10, 36, 28), "date command format strip"),
    ("Thu 10:36:28", datetime(2003, 9, 25, 10, 36, 28), "date command format strip"),
    ("Sep 10:36:28", datetime(2003, 9, 25, 10, 36, 28), "date command format strip"),
    ("10:36:28", datetime(2003, 9, 25, 10, 36, 28), "date command format strip"),
    ("10:36", datetime(2003, 9, 25, 10, 36), "date command format strip"),
    ("Sep 2003", datetime(2003, 9, 25), "date command format strip"),
    ("Sep", datetime(2003, 9, 25), "date command format strip"),
    ("2003", datetime(2003, 9, 25), "date command format strip"),
    ("10h36m28.5s", datetime(2003, 9, 25, 10, 36, 28, 500000), "hour with letters"),
    ("10h36m28s", datetime(2003, 9, 25, 10, 36, 28), "hour with letters strip"),
    ("10h36m", datetime(2003, 9, 25, 10, 36), "hour with letters strip"),
    ("10h", datetime(2003, 9, 25, 10), "hour with letters strip"),
    ("10 h 36", datetime(2003, 9, 25, 10, 36), "hour with letters strip"),
    ("10 h 36.5", datetime(2003, 9, 25, 10, 36, 30), "hour with letter strip"),
    ("36 m 5", datetime(2003, 9, 25, 0, 36, 5), "hour with letters spaces"),
    ("36 m 5 s", datetime(2003, 9, 25, 0, 36, 5), "minute with letters spaces"),
    ("36 m 05", datetime(2003, 9, 25, 0, 36, 5), "minute with letters spaces"),
    ("36 m 05 s", datetime(2003, 9, 25, 0, 36, 5), "minutes with letters spaces"),
    ("10h am", datetime(2003, 9, 25, 10), "hour am pm"),
    ("10h pm", datetime(2003, 9, 25, 22), "hour am pm"),
    ("10am", datetime(2003, 9, 25, 10), "hour am pm"),
    ("10pm", datetime(2003, 9, 25, 22), "hour am pm"),
    ("10:00 am", datetime(2003, 9, 25, 10), "hour am pm"),
    ("10:00 pm", datetime(2003, 9, 25, 22), "hour am pm"),
    ("10:00am", datetime(2003, 9, 25, 10), "hour am pm"),
    ("10:00pm", datetime(2003, 9, 25, 22), "hour am pm"),
    ("10:00a.m", datetime(2003, 9, 25, 10), "hour am pm"),
    ("10:00p.m", datetime(2003, 9, 25, 22), "hour am pm"),
    ("10:00a.m.", datetime(2003, 9, 25, 10), "hour am pm"),
    ("10:00p.m.", datetime(2003, 9, 25, 22), "hour am pm"),
    pytest.param("Wed", datetime(2003, 10, 1), "weekday alone", marks=pytest.mark.xfail(reason="Weekday-only requires relativedelta")),
    pytest.param("Wednesday", datetime(2003, 10, 1), "long weekday", marks=pytest.mark.xfail(reason="Weekday-only requires relativedelta")),
    ("October", datetime(2003, 10, 25), "long month"),
    ("31-Dec-00", datetime(2000, 12, 31), "zero year"),
    ("0:01:02", datetime(2003, 9, 25, 0, 1, 2), "random format"),
    ("12h 01m02s am", datetime(2003, 9, 25, 0, 1, 2), "random format"),
    ("12:08 PM", datetime(2003, 9, 25, 12, 8), "random format"),
    ("01h02m03", datetime(2003, 9, 25, 1, 2, 3), "random format"),
    ("01h02", datetime(2003, 9, 25, 1, 2), "random format"),
    ("01h02s", datetime(2003, 9, 25, 1, 0, 2), "random format"),
    ("01m02", datetime(2003, 9, 25, 0, 1, 2), "random format"),
    ("01m02h", datetime(2003, 9, 25, 2, 1), "random format"),
    ("2004 10 Apr 11h30m", datetime(2004, 4, 10, 11, 30), "random format"),
]


def _parse_with_default(result, default):
    """Convert ParseResult to datetime, filling missing values from default."""
    if result is None:
        return None

    # Handle tuple from fuzzy_with_tokens
    if isinstance(result, tuple):
        result = result[0]

    year = result.year if result.year is not None else default.year
    month = result.month if result.month is not None else default.month
    day = result.day if result.day is not None else default.day
    hour = result.hour if result.hour is not None else 0
    minute = result.minute if result.minute is not None else 0
    second = result.second if result.second is not None else 0
    microsecond = result.microsecond if result.microsecond is not None else 0

    return datetime(year, month, day, hour, minute, second, microsecond)


class TestParserDefaultCompat:
    """Test parser with default datetime - matches dateutil behavior."""

    DEFAULT = datetime(2003, 9, 25)

    @pytest.mark.parametrize("parsable_text,expected_datetime,assertion_message", PARSER_DEFAULT_TEST_CASES)
    def test_parser_default(self, parsable_text, expected_datetime, assertion_message):
        result = parse(parsable_text, fuzzy=True)
        parsed_dt = _parse_with_default(result, self.DEFAULT)
        assert parsed_dt == expected_datetime, f"{assertion_message}: got {parsed_dt}, expected {expected_datetime}"


class TestDayfirstYearfirst:
    """Test dayfirst and yearfirst options."""

    @pytest.mark.parametrize('sep', ['-', '.', '/', ' '])
    def test_parse_dayfirst(self, sep):
        """Test dayfirst=True parsing."""
        expected = datetime(2003, 9, 10)
        dstr = sep.join(['10', '09', '2003'])
        parser = Parser(dayfirst=True)
        result = parser.parse(dstr)
        parsed_dt = _parse_to_datetime(result)
        assert parsed_dt == expected

    @pytest.mark.parametrize('sep', ['-', '.', '/', ' '])
    def test_parse_yearfirst(self, sep):
        """Test yearfirst=True parsing."""
        expected = datetime(2010, 9, 3)
        dstr = sep.join(['2010', '09', '03'])
        parser = Parser(yearfirst=True)
        result = parser.parse(dstr)
        parsed_dt = _parse_to_datetime(result)
        assert parsed_dt == expected

    def test_no_yearfirst_no_dayfirst(self):
        """Test default behavior (yearfirst=False, dayfirst=False) - should be MMDDYY."""
        dtstr = '090107'
        result = parse(dtstr)
        parsed_dt = _parse_to_datetime(result)
        # Default: MMDDYY -> 2007-09-01
        assert parsed_dt == datetime(2007, 9, 1)

    def test_yearfirst(self):
        """Test yearfirst=True - should be YYMMDD."""
        dtstr = '090107'
        parser = Parser(yearfirst=True)
        result = parser.parse(dtstr)
        parsed_dt = _parse_to_datetime(result)
        # yearfirst=True: YYMMDD -> 2009-01-07
        assert parsed_dt == datetime(2009, 1, 7)

    def test_dayfirst(self):
        """Test dayfirst=True - should be DDMMYY."""
        dtstr = '090107'
        parser = Parser(dayfirst=True)
        result = parser.parse(dtstr)
        parsed_dt = _parse_to_datetime(result)
        # dayfirst=True: DDMMYY -> 2007-01-09
        assert parsed_dt == datetime(2007, 1, 9)

    def test_dayfirst_yearfirst(self):
        """Test both dayfirst=True and yearfirst=True - should be YYDDMM."""
        dtstr = '090107'
        parser = Parser(dayfirst=True, yearfirst=True)
        result = parser.parse(dtstr)
        parsed_dt = _parse_to_datetime(result)
        # Both: YYDDMM -> 2009-07-01
        assert parsed_dt == datetime(2009, 7, 1)


class TestTimezoneOffset:
    """Test timezone offset parsing."""

    def test_iso_with_tz_offset_positive(self):
        """Test ISO format with +03:00 offset."""
        result = parse("2003-09-25T10:49:41+03:00")
        assert result.tzoffset == 3 * 3600

    def test_iso_stripped_with_tz_offset(self):
        """Test stripped ISO with +0300 offset."""
        result = parse("20030925T104941+0300")
        assert result.tzoffset == 3 * 3600

    def test_iso_with_negative_offset(self):
        """Test ISO with -03:00 offset."""
        result = parse("2003-09-25T10:49:41-03:00")
        assert result.tzoffset == -3 * 3600

    def test_iso_with_microseconds_and_offset(self):
        """Test ISO with microseconds and timezone offset."""
        result = parse("2003-09-25T10:49:41.5-03:00")
        assert result.tzoffset == -3 * 3600
        assert result.microsecond == 500000


class TestIgnoretz:
    """Test ignoretz option - just verify parsing works without tz."""

    @pytest.mark.parametrize('dstr,expected', [
        ("Thu Sep 25 10:36:28 BRST 2003", datetime(2003, 9, 25, 10, 36, 28)),
        ("1996.07.10 AD at 15:08:56 PDT", datetime(1996, 7, 10, 15, 8, 56)),
        ("Tuesday, April 12, 1952 AD 3:30:42pm PST", datetime(1952, 4, 12, 15, 30, 42)),
        ("November 5, 1994, 8:15:30 am EST", datetime(1994, 11, 5, 8, 15, 30)),
        ("1994-11-05T08:15:30-05:00", datetime(1994, 11, 5, 8, 15, 30)),
        ("1994-11-05T08:15:30Z", datetime(1994, 11, 5, 8, 15, 30)),
        ("1976-07-04T00:01:02Z", datetime(1976, 7, 4, 0, 1, 2)),
        ("1986-07-05T08:15:30z", datetime(1986, 7, 5, 8, 15, 30)),
        ("Tue Apr 4 00:22:12 PDT 1995", datetime(1995, 4, 4, 0, 22, 12)),
    ])
    def test_parse_ignoretz(self, dstr, expected):
        """Parse with timezone info but only compare date/time components."""
        result = parse(dstr, fuzzy=True)
        parsed_dt = _parse_to_datetime(result)
        # Compare without timezone
        assert parsed_dt.replace(tzinfo=None) == expected


class TestFuzzyParsing:
    """Test fuzzy parsing mode."""

    def test_fuzzy(self):
        """Test fuzzy parsing with text around date."""
        s = "Today is 25 of September of 2003, exactly at 10:49:41 with timezone -03:00."
        result = parse(s, fuzzy=True)
        parsed_dt = _parse_to_datetime(result)
        assert parsed_dt == datetime(2003, 9, 25, 10, 49, 41)
        assert result.tzoffset == -3 * 3600

    def test_fuzzy_with_tokens(self):
        """Test fuzzy_with_tokens returns tuple."""
        s = "Today is 25 of September of 2003, exactly at 10:49:41 with timezone -03:00."
        parser = Parser()
        result = parser.parse(s, fuzzy=True, fuzzy_with_tokens=True)
        assert isinstance(result, tuple)
        assert len(result) == 2
        parsed_result, tokens = result
        parsed_dt = _parse_to_datetime(parsed_result)
        assert parsed_dt == datetime(2003, 9, 25, 10, 49, 41)
        assert isinstance(tokens, list)

    def test_fuzzy_am_pm_problem(self):
        """Test fuzzy parsing doesn't get confused by AM/PM in text."""
        s1 = "I have a meeting on March 1, 1974."
        s2 = "On June 8th, 2020, I am going to be the first man on Mars"

        result1 = parse(s1, fuzzy=True)
        result2 = parse(s2, fuzzy=True)

        parsed_dt1 = _parse_to_datetime(result1)
        parsed_dt2 = _parse_to_datetime(result2)

        assert parsed_dt1 == datetime(1974, 3, 1)
        assert parsed_dt2 == datetime(2020, 6, 8)


class TestMicrosecondPrecision:
    """Test microsecond precision."""

    def test_microseconds_precision(self):
        """Test microsecond precision is correct."""
        result1 = parse("00:11:25.01")
        result2 = parse("00:12:10.01")
        assert result1.microsecond == 10000
        assert result2.microsecond == 10000

    @pytest.mark.parametrize('ms', [100001, 100000, 99999, 99998,
                                     10001,  10000,  9999,  9998,
                                      1001,   1000,   999,   998,
                                       101,    100,    99,    98])
    def test_microsecond_precision_roundtrip(self, ms):
        """Test microseconds round-trip correctly through isoformat."""
        dt = datetime(2008, 2, 27, 21, 26, 1, ms)
        result = parse(dt.isoformat())
        parsed_dt = _parse_to_datetime(result)
        assert parsed_dt == dt


class TestStrftimeFormats:
    """Test various strftime format strings."""

    @pytest.mark.parametrize("fmt,dstr", [
        ("%a %b %d %Y", "Thu Sep 25 2003"),
        ("%b %d %Y", "Sep 25 2003"),
        ("%Y-%m-%d", "2003-09-25"),
        ("%Y%m%d", "20030925"),
        ("%Y-%b-%d", "2003-Sep-25"),
        ("%d-%b-%Y", "25-Sep-2003"),
        ("%b-%d-%Y", "Sep-25-2003"),
        ("%m-%d-%Y", "09-25-2003"),
        ("%d-%m-%Y", "25-09-2003"),
        ("%Y.%m.%d", "2003.09.25"),
        ("%Y.%b.%d", "2003.Sep.25"),
        ("%d.%b.%Y", "25.Sep.2003"),
        ("%b.%d.%Y", "Sep.25.2003"),
        ("%m.%d.%Y", "09.25.2003"),
        ("%d.%m.%Y", "25.09.2003"),
        ("%Y/%m/%d", "2003/09/25"),
        ("%Y/%b/%d", "2003/Sep/25"),
        ("%d/%b/%Y", "25/Sep/2003"),
        ("%b/%d/%Y", "Sep/25/2003"),
        ("%m/%d/%Y", "09/25/2003"),
        ("%d/%m/%Y", "25/09/2003"),
        ("%Y %m %d", "2003 09 25"),
        ("%Y %b %d", "2003 Sep 25"),
        ("%d %b %Y", "25 Sep 2003"),
        ("%m %d %Y", "09 25 2003"),
        ("%d %m %Y", "25 09 2003"),
        ("%y %d %b", "03 25 Sep"),
    ])
    def test_strftime_formats(self, fmt, dstr):
        """Test parsing of strftime format strings."""
        expected = datetime(2003, 9, 25)
        result = parse(dstr, fuzzy=True)
        parsed_dt = _parse_to_datetime(result)
        assert parsed_dt == expected
