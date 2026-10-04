"""Extended parser tests - ported from dateutil test_parser.py.

These tests cover more complex parsing scenarios and edge cases.
"""

import pytest

from opendate._opendate import Parser, parse


class TestParserMoreFormats:
    """Test additional date/time formats from dateutil.
    """

    def test_parse_date_with_spaces(self):
        """Test date with spaces: Jan 15 2024.

        Mutation: a comma after the day made mandatory.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('Jan 15 2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_date_dot_separator(self):
        """Test date with dot separator: 15.01.2024.

        Mutation: a dot-joined date read as a decimal number.
        Oracle: fields hand-read from the literal input under dayfirst.
        """
        parser = Parser(dayfirst=True)
        r = parser.parse('15.01.2024')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_parse_date_year_first(self):
        """Test date with year first: 2024/01/15.

        Mutation: a leading 4-digit field read as month or day.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('2024/01/15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    @pytest.mark.parametrize(
        'text',
        [
            'Jan 15, 2024, 10:30',
            'Jan 15, 2024 at 10:30',
            '10:30 on Jan 15, 2024',
            ])
    def test_parse_datetime_with_words(self, text):
        """Test date and time joined by a comma, 'at' or 'on'.

        Mutation: a joining word ends the parse, so the time or date
            after it is lost.
        Oracle: fields hand-read from the literal input.
        """
        r = parse(text, fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30

    def test_parse_datetime_space_separator(self):
        """Test datetime with space separator.

        Mutation: a space between date and time ends the parse.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('2024-01-15 10:30:45')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour == 10
        assert r.minute == 30
        assert r.second == 45


class TestParserMicroseconds:
    """Test microsecond parsing.
    """

    @pytest.mark.parametrize(
        ('text', 'microsecond'),
        [
            ('2024-01-15T10:30:45.123456', 123456),
            ('2024-01-15T10:30:45.123', 123000),
            ('2024-01-15T10:30:45.1', 100000),
            ('2024-01-15T10:30:45,123456', 123456),
            ])
    def test_parse_microseconds(self, text, microsecond):
        """Test 6-, 3- and 1-digit fractions, and a comma decimal mark.

        Mutation: a short fraction read as a whole count (.1 as 1 us), or
            the comma mark rejected.
        Oracle: hand-scaled fractions of a second in microseconds.
        """
        r = parse(text)
        assert r.microsecond == microsecond


class TestParserTimezoneOffsets:
    """Test timezone offset parsing.
    """

    @pytest.mark.parametrize(
        ('text', 'tzoffset'),
        [
            ('2024-01-15T10:30:00+05:30', 5 * 3600 + 30 * 60),
            ('2024-01-15T10:30:00-05:30', -(5 * 3600 + 30 * 60)),
            ('2024-01-15T10:30:00+0530', 5 * 3600 + 30 * 60),
            ('2024-01-15T10:30:00-0800', -8 * 3600),
            ('2024-01-15T10:30:00+05', 5 * 3600),
            ])
    def test_parse_offsets(self, text, tzoffset):
        """Test +HH:MM, -HH:MM, +HHMM, -HHMM and +HH offsets.

        Mutation: the minus sign applied to the hours only, or a
            colon-free or hour-only offset rejected.
        Oracle: hand-computed offsets in seconds.
        """
        r = parse(text)
        assert r.tzoffset == tzoffset

    @pytest.mark.parametrize(
        ('text', 'tzname'),
        [
            ('2024-01-15 10:30:00 EST', 'EST'),
            ('2024-01-15 10:30:00 PST', 'PST'),
            ('2024-01-15 10:30:00 CET', 'CET'),
            ])
    def test_parse_named_zones(self, text, tzname):
        """Test a named zone keeps its name.

        Mutation: a zone name dropped or folded into another token.
        Oracle: the name as written in the input.
        """
        r = parse(text)
        assert r.tzname == tzname


class TestParserAMPM:
    """Test AM/PM parsing.
    """

    @pytest.mark.parametrize(
        ('text', 'hour', 'minute'),
        [
            ('10:30 am', 10, 30),
            ('2:30 pm', 14, 30),
            ('10:30 AM', 10, 30),
            ('2:30 PM', 14, 30),
            ('10:30 a.m.', 10, 30),
            ('2:30 p.m.', 14, 30),
            ('12:00 AM', 0, 0),
            ('12:00 PM', 12, 0),
            ('12:30 AM', 0, 30),
            ('12:30 PM', 12, 30),
            ])
    def test_parse_ampm(self, text, hour, minute):
        """Test am/pm in each case and dotted form, and the 12 o'clock rule.

        Mutation: 12 PM moved to 24 or 12 AM left at 12, or the marker
            matched case-sensitively.
        Oracle: 12-hour clock rules: PM adds 12 except at 12, AM maps 12
            to 0.
        """
        r = parse(text)
        assert r.hour == hour
        assert r.minute == minute


class TestParserDayFirst:
    """Test dayfirst option.
    """

    def test_dayfirst_false(self):
        """Test MM/DD/YYYY with dayfirst=False.

        Mutation: dayfirst=False read as dayfirst=True.
        Oracle: 15 cannot be a month, so 01/15 reads as January 15.
        """
        parser = Parser(dayfirst=False)
        r = parser.parse('01/15/2024')
        assert r.month == 1
        assert r.day == 15

    def test_dayfirst_true(self):
        """Test DD/MM/YYYY with dayfirst=True.

        Mutation: Parser drops its dayfirst flag.
        Oracle: 15 cannot be a month, so 15/01 reads as January 15.
        """
        parser = Parser(dayfirst=True)
        r = parser.parse('15/01/2024')
        assert r.day == 15
        assert r.month == 1

    def test_dayfirst_ambiguous(self):
        """Test 05/06/2024 reads as May 6 by default, 5 June under dayfirst.

        Mutation: dayfirst ignored when both fields could be a month.
        Oracle: MM/DD order by default, DD/MM order under dayfirst.
        """
        r1 = parse('05/06/2024')
        assert r1.month == 5
        assert r1.day == 6

        parser = Parser(dayfirst=True)
        r2 = parser.parse('05/06/2024')
        assert r2.day == 5
        assert r2.month == 6


class TestParserYearFirst:
    """Test yearfirst option.
    """

    def test_yearfirst_false(self):
        """Test MM/DD/YY with yearfirst=False.

        Mutation: yearfirst=False read as yearfirst=True.
        Oracle: fields hand-read in MM/DD/YY order.
        """
        parser = Parser(yearfirst=False)
        r = parser.parse('01/15/24')
        assert r.month == 1
        assert r.day == 15
        assert r.year == 2024

    def test_yearfirst_true(self):
        """Test YY/MM/DD with yearfirst=True.

        Mutation: Parser drops its yearfirst flag.
        Oracle: fields hand-read in YY/MM/DD order.
        """
        parser = Parser(yearfirst=True)
        r = parser.parse('24/01/15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15


class TestParserSpecialFormats:
    """Test special format parsing.
    """

    def test_parse_ordinal_day(self):
        """Test ordinal day: January 15th, 2024.

        Mutation: an ordinal suffix stops the day being read.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('January 15th, 2024', fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    @pytest.mark.parametrize(
        ('text', 'day'),
        [
            ('January 1st, 2024', 1),
            ('January 2nd, 2024', 2),
            ('January 3rd, 2024', 3),
            ])
    def test_parse_ordinal_suffixes(self, text, day):
        """Test the 1st, 2nd and 3rd suffixes.

        Mutation: only the 'th' suffix recognized.
        Oracle: the day number before the suffix.
        """
        r = parse(text, fuzzy=True)
        assert r.day == day

    def test_parse_year_month(self):
        """Test year-month only: 2024-01.

        Mutation: a trailing 2-digit field after the year read as a day.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('2024-01')
        assert r.year == 2024
        assert r.month == 1

    def test_parse_month_year(self):
        """Test month year: January 2024.

        Mutation: a 4-digit field after a month name read as a day.
        Oracle: fields hand-read from the literal input.
        """
        r = parse('January 2024')
        assert r.year == 2024
        assert r.month == 1

    def test_parse_year_only(self):
        """Test year only: 2024.

        Mutation: a lone 4-digit number read as HHMM.
        Oracle: the literal input.
        """
        r = parse('2024')
        assert r.year == 2024


class TestParserFuzzyMode:
    """Test fuzzy parsing mode.
    """

    @pytest.mark.parametrize(
        'text',
        [
            'Today is 2024-01-15',
            '2024-01-15 was yesterday',
            'The date 2024-01-15 is important',
            'Order #12345 placed on 2024-01-15',
            ])
    def test_fuzzy_skips_text(self, text):
        """Test fuzzy mode skips leading, trailing and surrounding text.

        Mutation: a stray number such as #12345 taken as a date field, or
            text on one side of the date not skipped.
        Oracle: fields hand-read from the embedded date.
        """
        r = parse(text, fuzzy=True)
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15

    def test_fuzzy_with_tokens_returns_tuple(self):
        """Test fuzzy_with_tokens returns the result and the skipped tokens.

        Mutation: fuzzy_with_tokens ignored, or the skipped text discarded.
        Oracle: 'Today is ' precedes the date, so tokens is not empty.
        """
        parser = Parser()
        result = parser.parse('Today is 2024-01-15', fuzzy=True, fuzzy_with_tokens=True)
        assert isinstance(result, tuple)
        assert len(result) == 2
        r, tokens = result
        assert r.year == 2024
        assert isinstance(tokens, list)
        assert len(tokens) > 0


class TestParserEdgeCases:
    """Test edge cases and special scenarios.
    """

    def test_parse_date_only(self):
        """Test parsing date only.

        Mutation: missing time fields filled with 0 in place of None.
        Oracle: the input carries no time, so hour and minute stay None.
        """
        r = parse('2024-01-15')
        assert r.year == 2024
        assert r.month == 1
        assert r.day == 15
        assert r.hour is None
        assert r.minute is None

    def test_parse_month_name_case_insensitive(self):
        """Test month name is case insensitive.

        Mutation: month names matched case-sensitively.
        Oracle: the three spellings name the same month, January.
        """
        r1 = parse('JANUARY 15, 2024')
        r2 = parse('january 15, 2024')
        r3 = parse('January 15, 2024')
        assert r1.month == r2.month == r3.month == 1

    def test_parse_weekday_case_insensitive(self):
        """Test weekday is case insensitive.

        Mutation: weekday names matched case-sensitively.
        Oracle: both spellings name Monday, weekday 0.
        """
        r1 = parse('MONDAY, January 15, 2024', fuzzy=True)
        r2 = parse('monday, January 15, 2024', fuzzy=True)
        assert r1.weekday == r2.weekday == 0
