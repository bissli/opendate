import copy
import datetime
import pathlib
import pickle

import numpy as np
import pandas as pd
import pendulum
import pytest
from opendate import WEEKDAY_SHORTNAME, Date, WeekDay, expect_date
from opendate import get_calendar


def test_end_of_week():
    """Get the end date of the week.

    Mutation: business end_of('week') keeping the Sunday, or stopping on
        Good Friday instead of rolling back past it.
    Oracle: hand-read 2020 and 2023 calendars - Sunday ends the week,
        and NYSE closed on Good Friday, 2020-04-10.
    """

    # Regular Monday
    d = Date(2023, 4, 24).end_of('week')
    assert d == Date(2023, 4, 30)

    # Regular Sunday
    d = Date(2023, 4, 30).end_of('week')
    assert d == Date(2023, 4, 30)

    # Good Friday
    d = Date(2020, 4, 12).end_of('week')
    assert d == Date(2020, 4, 12)
    d = Date(2020, 4, 10).end_of('week')
    assert d == Date(2020, 4, 12)

    d = Date(2020, 4, 10)\
        .business()\
        .end_of('week')
    assert d == Date(2020, 4, 9)

    d = Date(2020, 4, 9)\
        .end_of('week')\
        .business()\
        .subtract(days=1)
    assert d == Date(2020, 4, 9)


def test_next_friday():
    """Get next end of week (Friday).

    Mutation: next(FRIDAY) returning the start date when it is already
        a Friday.
    Oracle: hand-read calendar - 2018-10-08 is a Monday and 2018-10-12
        a Friday.
    """

    d = Date.instance(datetime.datetime(2018, 10, 8, 0, 0, 0)).next(WeekDay.FRIDAY)
    assert d == Date(2018, 10, 12)

    d = Date(2018, 10, 12).next(WeekDay.FRIDAY)
    assert d == Date(2018, 10, 19)


def test_start_of_week():
    """Start of week function (Monday unless not a holiday).

    Mutation: business start_of('week') keeping a holiday Monday instead
        of rolling forward to Tuesday.
    Oracle: hand-read calendar - NYSE closed on Memorial Day, 2020-05-25.
    """

    # Regular Monday
    d = Date(2023, 4, 24).start_of('week')
    assert d == Date(2023, 4, 24)

    # Regular Sunday
    d = Date(2023, 4, 30).start_of('week')
    assert d == Date(2023, 4, 24)

    # Memorial day 5/25
    d = Date(2020, 5, 25).start_of('week')
    assert d == Date(2020, 5, 25)
    d = Date(2020, 5, 27).start_of('week')
    assert d == Date(2020, 5, 25)
    d = Date(2020, 5, 26)\
        .business()\
        .start_of('week')
    assert d == Date(2020, 5, 26)


def test_end_of_month():
    """End of month.

    Mutation: business end_of('month') keeping a weekend month end.
    Oracle: hand-read calendar - 2023-04-30 is a Sunday, so the last
        business day is Friday 2023-04-28.
    """

    d = Date(2021, 6, 15).end_of('month')
    assert d == Date(2021, 6, 30)
    d = Date(2021, 6, 30).end_of('month')
    assert d == Date(2021, 6, 30)

    # Sunday -> Friday
    d =  Date(2023, 4, 30)\
        .business()\
        .end_of('month')
    assert d == Date(2023, 4, 28)


def test_previous_end_of_month():
    """Previous EOM.

    Mutation: start_of('month') landing on a day other than the first,
        so one day back stays inside May.
    Oracle: hand-computed - April has 30 days.
    """

    d = Date(2021, 5, 30)\
        .start_of('month')\
        .subtract(days=1)
    assert d == Date(2021, 4, 30)


def test_previous_start_of_month():
    """Previous first of month.

    Mutation: business start_of('month') keeping a weekend first of month
        instead of rolling forward.
    Oracle: hand-read calendar - 2021-05-01 is a Saturday, so the first
        business day is Monday 2021-05-03.
    """

    d =  Date(2021, 6, 15)\
        .start_of('month')\
        .subtract(days=1)\
        .start_of('month')
    assert d == Date(2021, 5, 1)

    d = Date(2021, 6, 15)\
        .start_of('month')\
        .subtract(days=1)\
        .business()\
        .start_of('month')
    assert d == Date(2021, 5, 3)


def test_first_of_year():
    """Verify first_of('year') returns January 1 of the date's year.

    Mutation: first_of('year') returning the first of the current month,
        or the first business day.
    Oracle: hand-written January 1 of each year.
    """

    assert Date.today().first_of('year') == datetime.date(pendulum.today().year, 1, 1)

    assert Date(2012, 12, 31).first_of('year') == datetime.date(2012, 1, 1)


def test_last_of_year():
    """Verify last_of('year') returns December 31 of the date's year.

    Mutation: last_of('year') returning the last of the month or quarter.
    Oracle: hand-written 2022-12-31.
    """

    d = Date(2022, 4, 2).last_of('year')
    assert d == Date(2022, 12, 31)


def test_last_of_quarter():
    """Return the quarter start or quarter end of a given date.

    Mutation: quarters offset by a month, or a quarter-end date moved
        into the next quarter.
    Oracle: hand-read calendar quarters ending Mar 31 and Dec 31.
    """

    d = Date(2013, 11, 5).last_of('quarter')
    assert d == Date(2013, 12, 31)

    d = Date(2016, 3, 31).last_of('quarter')
    assert d == Date(2016, 3, 31)


def test_first_of_quarter():
    """Return the quarter start or quarter end of a given date.

    Mutation: quarters offset by a month, so Q4 starts Nov 1.
    Oracle: hand-read calendar quarters starting Jan 1 and Oct 1.
    """

    d =  Date(2013, 11, 5).first_of('quarter')
    assert d == Date(2013, 10, 1)

    d = Date(1999, 1, 19).first_of('quarter')
    assert d == Date(1999, 1, 1)


def test_last_quarter_date():
    """Return the previous quarter start or quarter end of a given date.

    Mutation: first_of('quarter') off by a month, or a step back that
        fails to cross the year boundary.
    Oracle: hand-read calendar quarters, two of them across a year end.
    """

    d = Date(2013, 11, 5)\
        .first_of('quarter')\
        .subtract(days=1)
    assert d == Date(2013, 9, 30)
    d = Date.instance(datetime.date(2016, 3, 31))\
        .first_of('quarter')\
        .subtract(days=1)
    assert d == Date(2015, 12, 31)

    d = Date(2013, 11, 5)\
        .first_of('quarter')\
        .subtract(days=1)\
        .first_of('quarter')
    assert d == Date(2013, 7, 1)
    d = Date.instance(datetime.date(1999, 1, 19))\
        .first_of('quarter')\
        .subtract(days=1)\
        .first_of('quarter')
    assert d == Date(1998, 10, 1)


def test_loaded_module():
    """We change the module signature. Check that Pendulum still works.

    Mutation: the metaclass patching pendulum.Date itself, so pendulum's
        own add breaks or moves by business days.
    Oracle: hand-computed 2000-01-01 plus 10 calendar days.
    """

    pendulum_date = pendulum.Date(2000, 1, 1)
    d = pendulum_date.add(days=10)
    assert d == Date(2000, 1, 11)


def test_add():
    """Verify business add skips weekends and NYSE closures.

    Mutation: business add counting the 2018-12-05 closure as open, an
        out-of-range date raising, or subtract ignoring a negative sign.
    Oracle: hand-counted NYSE sessions - closed 2018-12-05 for George
        H.W. Bush's funeral - and the 9999-12-31 sentinel.
    """
    i, thedate = 5, datetime.date(2018, 11, 29)
    while i > 0:
        thedate = Date.instance(thedate).b.add(days=1)
        i -= 1
    assert thedate == Date(2018, 12, 7)

    i, thedate = 5, datetime.date(2021, 11, 17)
    while i > 0:
        thedate = Date.instance(thedate).b.add(days=1)
        i -= 1
    assert thedate == Date(2021, 11, 24)

    d = Date.instance(datetime.date(9999, 12, 31))
    result = d.b.add(days=1)
    assert result == d

    d = Date.instance(datetime.date(2018, 11, 29)).b.add(days=5)
    assert d == Date(2018, 12, 7)
    d = Date(2021, 11, 17).b.add(days=5)
    assert d == Date(2021, 11, 24)

    d = Date.instance(datetime.date(2018, 11, 29)).b.subtract(days=-5)
    assert d == Date(2018, 12, 7)
    d = Date(2021, 11, 17).b.subtract(days=-5)
    assert d == Date(2021, 11, 24)


def test_subtract():
    """Verify business subtract skips weekends and NYSE closures.

    Mutation: business subtract counting the 2018-12-05 closure as open,
        or add ignoring a negative sign.
    Oracle: hand-counted NYSE sessions - closed 2018-12-05 for George
        H.W. Bush's funeral.
    """
    d = Date(2018, 12, 7).b.subtract(days=5)
    assert d == Date(2018, 11, 29)
    d = Date(2021, 11, 24).b.subtract(days=5)
    assert d == Date(2021, 11, 17)
    d = Date(2021, 11, 24).subtract(days=7)
    assert d == Date(2021, 11, 17)

    d = Date(2018, 12, 7).b.add(days=-5)
    assert d == Date(2018, 11, 29)
    d = Date(2021, 11, 24).add(days=-7)
    assert d == Date(2021, 11, 17)


def test_negative_days_calendar():
    """Test add/subtract with negative days in calendar (non-business) mode.

    Mutation: add or subtract taking the absolute value of a negative
        count, or dropping the sign for months and weeks.
    Oracle: hand-computed calendar dates, two across a month or year end.
    """
    # add(days=-N) goes backward
    assert Date(2024, 4, 1).add(days=-1) == Date(2024, 3, 31)
    assert Date(2024, 4, 1).add(days=-3) == Date(2024, 3, 29)
    assert Date(2024, 1, 1).add(days=-1) == Date(2023, 12, 31)

    # subtract(days=-N) goes forward
    assert Date(2024, 4, 1).subtract(days=-1) == Date(2024, 4, 2)
    assert Date(2024, 12, 31).subtract(days=-1) == Date(2025, 1, 1)

    # equivalence: add(days=-N) == subtract(days=N)
    assert Date(2024, 6, 15).add(days=-10) == Date(2024, 6, 15).subtract(days=10)
    assert Date(2024, 6, 15).subtract(days=-10) == Date(2024, 6, 15).add(days=10)

    # negative with other units
    assert Date(2024, 4, 15).add(months=-1) == Date(2024, 3, 15)
    assert Date(2024, 4, 15).subtract(months=-1) == Date(2024, 5, 15)
    assert Date(2024, 4, 15).add(weeks=-2) == Date(2024, 4, 1)
    assert Date(2024, 4, 15).subtract(weeks=-2) == Date(2024, 4, 29)


def test_set_calendar():
    """Test setting calendar on Date.

    Mutation: business add counting the Saturday start date as a step.
    Oracle: hand-counted weekdays - 2000-01-01 is a Saturday, and the
        tenth session after it is Friday 2000-01-14.
    """
    d = Date(2000, 1, 1).calendar('NYSE').b.add(days=10)
    assert d == Date(2000, 1, 14)


def start_of_month_weekday(self, weekday='MO'):
    """Get first X of the month

    >>> Date(2014, 8, 1).start_of_month_weekday('WE')
    Date(2014, 8, 6)
    >>> Date(2014, 7, 31).start_of_month_weekday('WE')
    Date(2014, 7, 2)
    >>> Date(2014, 8, 6).start_of_month_weekday('WE')
    Date(2014, 8, 6)
    """
    return self.start_of('month').next(WEEKDAY_SHORTNAME.get(weekday))


def end_of_month_weekday(self, weekday='SU'):
    """Like `start`, but for the end X weekday of month"""
    return self.end_of('month').previous(WEEKDAY_SHORTNAME.get(weekday))


def test_parse():
    """Test Date.parse with various input formats.

    Mutation: 'P' computed as calendar yesterday, an offset sign flipped,
        a two-digit year read in the 1900s, or a numeric string that is
        not 8 digits parsed as a date.
    Oracle: the same business arithmetic through Date.b, and hand-written
        dates.
    """
    # Business day calculations
    assert Date.parse('T-3b') == Date.today().b.subtract(days=3)
    assert Date.parse('T-3b') == Date.today().b.add(days=-3)
    assert Date.parse('T+3b') == Date.today().b.subtract(days=-3)

    assert Date.parse('P') == Date.today().b.subtract(days=1)
    assert Date.parse('P') == Date.today().b.add(days=-1)
    assert Date.parse('P-3b') == Date.today().b.add(days=-1).b.subtract(days=3)
    assert Date.parse('P-3b') == Date.today().b.subtract(days=1).b.add(days=-3)
    assert Date.parse('P+3b') == Date.today().b.add(days=-1).b.subtract(days=-3)
    assert Date.parse('P+3b') == Date.today().b.subtract(days=1).b.subtract(days=-3)

    # Standard date formats
    assert Date.parse('01/11/19') == Date(2019, 1, 11)
    assert Date.parse('01/15/20') == Date(2020, 1, 15)
    assert Date.parse('01/15/21') == Date(2021, 1, 15)
    assert Date.parse('01/15/22') == Date(2022, 1, 15)

    # Invalid input
    assert Date.parse('100.264400') is None


@pytest.mark.parametrize(
    ('input_str', 'expected'),
    [
        # m/d/yyyy format (with 4-digit year)
        ('6-23-2006', Date(2006, 6, 23)),
        ('01/15/2024', Date(2024, 1, 15)),
        # m/d/yy format (with 2-digit year)
        ('6/23/06', Date(2006, 6, 23)),
        # yyyy-mm-dd format
        ('2006-6-23', Date(2006, 6, 23)),
        # yyyymmdd format
        ('20060623', Date(2006, 6, 23)),
        # Named month formats
        ('23-JUN-2006', Date(2006, 6, 23)),
        ('20 Jan 2009', Date(2009, 1, 20)),
        ('June 23, 2006', Date(2006, 6, 23)),
        ('23-May-12', Date(2012, 5, 23)),
        ('23May2012', Date(2012, 5, 23)),
        ('Jan. 13, 2014', Date(2014, 1, 13)),
        ('Jan-15-2024', Date(2024, 1, 15)),
        ('Jan 15 2024', Date(2024, 1, 15)),
        ])
def test_parse_date_formats(input_str, expected):
    """Test Date.parse with various date format strings.

    Mutation: month and day swapped in a numeric form, or a two-digit
        year read in the 1900s.
    Oracle: hand-written dates, each with a day above 12.
    """
    assert Date.parse(input_str) == expected


def test_parse_date_no_year():
    """Test m/d format (no year - uses current year).

    Mutation: a missing year resetting the month or day to 1.
    Oracle: the month and day written in the input, 01/15.
    """
    result = Date.parse('01/15')
    assert result.month == 1
    assert result.day == 15


def test_parse_special_strings():
    """Test Date.parse with special string keywords.

    Mutation: 'M' returning the first of the month, or the 'today' and
        'yester' match turned case-sensitive.
    Oracle: Date.today() and calendar arithmetic on it.
    """
    # Today variations
    assert Date.parse('T') == Date.today()
    assert Date.parse('TODAY') == Date.today()
    assert Date.parse('today') == Date.today()

    # Yesterday variations
    assert Date.parse('Y') == Date.today().subtract(days=1)
    assert Date.parse('Yesterday') == Date.today().subtract(days=1)

    # Month shortcuts
    assert Date.parse('M') == Date.today().start_of('month').subtract(days=1)


def test_parse_error_handling():
    """Test Date.parse error handling behavior.

    Mutation: raise_err ignored for empty input, or fuzzy parsing that
        turns plain words into a date.
    Oracle: None or ValueError for each input, per the parse contract.
    """
    # Default behavior - returns None
    assert Date.parse('bad date') is None
    assert Date.parse('invalid') is None
    assert Date.parse('') is None
    assert Date.parse(None) is None

    # raise_err behavior
    with pytest.raises(ValueError):
        Date.parse('bad date', raise_err=True)

    with pytest.raises(ValueError):
        Date.parse('', raise_err=True)

    with pytest.raises(ValueError):
        Date.parse(None, raise_err=True)


@pytest.mark.parametrize('copier', [copy.copy, copy.deepcopy])
def test_copy(copier):
    """Verify copy and deepcopy of a Date compare equal to the original.

    Mutation: a Date __new__ or metaclass hook that rejects the pickled
        form date.__reduce__ hands back.
    Oracle: the original Date, beside a plain pendulum.Date.
    """

    d = pendulum.Date(2022, 1, 1)
    assert copier(d) == d

    d = Date(2022, 1, 1)
    assert copier(d) == d


def test_pickle(tmp_path):
    """Test pickle serialization and deserialization of Date objects.

    Mutation: a Date __new__ or metaclass hook that rejects the pickled
        form date.__reduce__ hands back.
    Oracle: the original Date.
    """
    d = Date(2022, 1, 1)

    pickle_file = tmp_path / 'date.pkl'
    with pathlib.Path(pickle_file).open('wb') as f:
        pickle.dump(d, f)
    with pathlib.Path(pickle_file).open('rb') as f:
        d_ = pickle.load(f)

    assert d == d_


def test_expects():
    """Verify expect_date converts nested tuples and skips a DataFrame.

    Mutation: expect_date not recursing into a nested tuple, or trying
        to convert a DataFrame.
    Oracle: hand-built nesting of pendulum Dates and the Dates expected.
    """

    @expect_date
    def func(args):
        return args

    p = pendulum.Date(2022, 1, 1)
    d = Date(2022, 1, 1)
    df = pd.DataFrame([['foo', 1], ['bar', 2]], columns=['name', 'value'])

    assert func(p) == d
    assert func((p, p)) == [d, d]
    assert func(((p, p), p)) == [[d, d], d]
    assert isinstance(func((df, p))[0], pd.DataFrame)


@pytest.mark.parametrize(
    ('date', 'expected_week'),
    [
        (Date(2023, 1, 2), 1),
        (Date(2023, 4, 27), 17),
        (Date(2023, 12, 31), 52),
        (Date(2023, 1, 1), 52),
        ])
def test_isoweek(date, expected_week):
    """Test the isoweek method returns correct ISO week numbers.

    Mutation: isoweek counting calendar-year weeks (%U or %W) in place
        of ISO weeks.
    Oracle: ISO 8601 - 2023-01-01 is a Sunday, so it falls in week 52
        of 2022.
    """
    assert date.isoweek() == expected_week


def test_lookback():
    """Test lookback functionality with different units.

    Mutation: business mode stepping in business days rather than
        calendar units, or 'quarter' stepping one month.
    Oracle: hand-computed dates one unit back from 2018-12-07 and
        2024-04-05.
    """
    test_date = Date(2018, 12, 7)

    assert test_date.lookback('last') == Date(2018, 12, 6)
    assert test_date.lookback('day') == Date(2018, 12, 6)
    assert test_date.lookback('week') == Date(2018, 11, 30)
    assert test_date.lookback('month') == Date(2018, 11, 7)

    assert test_date.b.lookback('last') == Date(2018, 12, 6)
    assert test_date.b.lookback('month') == Date(2018, 11, 7)

    d = Date(2024, 4, 5)
    assert d.b.lookback('day') == Date(2024, 4, 4)
    assert d.b.lookback('last') == Date(2024, 4, 4)
    assert d.b.lookback('week') == Date(2024, 3, 28)
    assert d.b.lookback('month') == Date(2024, 3, 5)
    assert d.b.lookback('quarter') == Date(2024, 1, 5)
    assert d.b.lookback('year') == Date(2023, 4, 5)


def test_lookback_business_snaps_to_previous():
    """Lookback in business mode snaps past holidays to previous business day.

    Mutation: snapping forward to the next business day instead of back.
    Oracle: hand-read calendar - one month before 2024-04-29 is Good
        Friday 2024-03-29, a NYSE holiday, so Thursday 2024-03-28.
    """
    d = Date(2024, 4, 29)
    result = d.b.lookback('month')
    assert result == Date(2024, 3, 28)


def test_lookback_invalid_unit_returns_none():
    """Lookback with unrecognized unit returns None.

    Mutation: an unknown unit raising KeyError or falling back to a day.
    Oracle: None, per the lookback contract.
    """
    assert Date(2024, 1, 1).lookback('decade') is None


@pytest.mark.parametrize(
    ('year', 'month', 'expected'),
    [
        (2022, 6, Date(2022, 6, 15)),
        (2023, 3, Date(2023, 3, 15)),
        (2022, 12, Date(2022, 12, 21)),
        (2023, 6, Date(2023, 6, 21)),
        ])
def test_third_wednesday(year, month, expected):
    """Test third_wednesday class method.

    Mutation: a week off by one, giving the second or fourth Wednesday.
    Oracle: hand-read calendars, two months starting on a Wednesday and
        two that do not.
    """
    assert Date.third_wednesday(year, month) == expected


def test_nearest_start_and_end_of_month():
    """Test nearest_start_of_month and nearest_end_of_month methods.

    Mutation: the day-15 cutoff moved by one (< for <=).
    Oracle: days 15 and 16, either side of the cutoff, with hand-read
        business days for 2015.
    """
    assert Date(2015, 1, 1).nearest_start_of_month() == Date(2015, 1, 1)
    assert Date(2015, 1, 15).nearest_start_of_month() == Date(2015, 1, 1)
    assert Date(2015, 1, 16).nearest_start_of_month() == Date(2015, 2, 1)
    assert Date(2015, 1, 31).nearest_start_of_month() == Date(2015, 2, 1)

    assert Date(2015, 1, 15).b.nearest_start_of_month() == Date(2015, 1, 2)
    assert Date(2015, 1, 31).b.nearest_start_of_month() == Date(2015, 2, 2)

    assert Date(2015, 1, 1).nearest_end_of_month() == Date(2014, 12, 31)
    assert Date(2015, 1, 15).nearest_end_of_month() == Date(2014, 12, 31)
    assert Date(2015, 1, 16).nearest_end_of_month() == Date(2015, 1, 31)
    assert Date(2015, 1, 31).nearest_end_of_month() == Date(2015, 1, 31)

    assert Date(2015, 1, 15).b.nearest_end_of_month() == Date(2014, 12, 31)
    assert Date(2015, 1, 31).b.nearest_end_of_month() == Date(2015, 1, 30)


def test_nearest_start_of_month_business_snapping():
    """Test that nearest_start_of_month snaps (not snap+add) in business mode.

    Mutation: snapping to a business day and then adding one more.
    Oracle: the weekdays hand-read in the comments below.
    """
    # Early in month (day <= 15), start is business day
    # March 1, 2024 is Friday (business day)
    d = Date(2024, 3, 10).b.nearest_start_of_month()
    assert d == Date(2024, 3, 1), f'Expected March 1, got {d}'

    # Early in month, start is weekend
    # December 1, 2024 is Sunday -> December 2 is Monday
    d = Date(2024, 12, 10).b.nearest_start_of_month()
    assert d == Date(2024, 12, 2), f'Expected December 2, got {d}'

    # Late in month (day > 15), next month start is business day
    # April 1, 2024 is Monday (business day)
    d = Date(2024, 3, 20).b.nearest_start_of_month()
    assert d == Date(2024, 4, 1), f'Expected April 1, got {d}'

    # Late in month, next month start is weekend
    # December 1, 2024 is Sunday -> December 2 is Monday
    d = Date(2024, 11, 20).b.nearest_start_of_month()
    assert d == Date(2024, 12, 2), f'Expected December 2, got {d}'


def test_nearest_end_of_month_business_snapping():
    """Business nearest_end_of_month snaps to a business day, adding no step.

    Mutation: snapping to a business day and then subtracting one more.
    Oracle: the weekdays and Good Friday hand-read in the comments below.
    """
    # Early in month (day <= 15), prev month end is business day
    # Feb 29, 2024 is Thursday (business day)
    d = Date(2024, 3, 10).b.nearest_end_of_month()
    assert d == Date(2024, 2, 29), f'Expected Feb 29, got {d}'

    # Early in month, prev month end is weekend
    # June 30, 2024 is Sunday -> June 28 is Friday
    d = Date(2024, 7, 10).b.nearest_end_of_month()
    assert d == Date(2024, 6, 28), f'Expected June 28, got {d}'

    # Late in month (day > 15), current month end is weekend + holiday
    # March 31, 2024 is Sunday, March 29 is Good Friday (holiday)
    # -> March 28 is Thursday
    d = Date(2024, 3, 20).b.nearest_end_of_month()
    assert d == Date(2024, 3, 28), f'Expected March 28, got {d}'


def test_weekday_or_previous_friday():
    """Test weekday_or_previous_friday method.

    Mutation: a weekend day moving forward to Monday, or a Friday moving
        back a week.
    Oracle: hand-read calendar - 2019-10-03 to 2019-10-06 run Thursday
        to Sunday.
    """
    assert Date(2019, 10, 4).weekday_or_previous_friday() == Date(2019, 10, 4)
    assert Date(2019, 10, 3).weekday_or_previous_friday() == Date(2019, 10, 3)

    assert Date(2019, 10, 5).weekday_or_previous_friday() == Date(2019, 10, 4)
    assert Date(2019, 10, 6).weekday_or_previous_friday() == Date(2019, 10, 4)


def test_next_relative_date_of_week_by_day():
    """Test next_relative_date_of_week_by_day method.

    Mutation: a target weekday equal to the start date stepping a week
        ahead.
    Oracle: hand-read calendar - 2020-05-18 is a Monday and 2020-05-24
        a Sunday.
    """
    monday = Date(2020, 5, 18)
    sunday = Date(2020, 5, 24)
    assert monday.next_relative_date_of_week_by_day('SU') == sunday

    assert sunday.next_relative_date_of_week_by_day('SU') == sunday

    assert monday.next_relative_date_of_week_by_day('TU') == Date(2020, 5, 19)
    assert monday.next_relative_date_of_week_by_day('WE') == Date(2020, 5, 20)


def test_business_methods():
    """Test business day related methods.

    Mutation: the holiday table missing MLK Day or Thanksgiving, or the
        open time read in UTC (14:30) rather than New York time.
    Oracle: hand-read NYSE holidays - 2021-01-18 MLK Day,
        2021-11-25 Thanksgiving, 2024-05-27 Memorial Day - and the
        09:30 open.
    """
    assert Date(2021, 4, 19).is_business_day()
    assert not Date(2021, 4, 17).is_business_day()
    assert not Date(2021, 1, 18).is_business_day()
    assert not Date(2021, 11, 25).is_business_day()

    assert Date(2021, 4, 19).business_open()
    assert not Date(2021, 4, 17).business_open()

    open_time, close_time = Date(2023, 1, 5).business_hours()
    assert open_time is not None
    assert close_time is not None
    assert open_time.hour == 9
    assert open_time.minute == 30

    open_time, close_time = Date(2024, 5, 27).business_hours()
    assert open_time is None
    assert close_time is None


def test_out_of_range_date_noop():
    """Verify a date outside 1900-2100 is no business day and never moves.

    Mutation: the range check dropped, so a far date raises or reports
        a business day.
    Oracle: years 1899, 2101 and 9999, just and far outside the range.
    """
    d = Date(9999, 12, 31)
    assert d.is_business_day() is False

    d = Date(2101, 1, 1)
    assert d.is_business_day() is False

    d = Date(1899, 12, 31)
    assert d.is_business_day() is False

    d = Date(9999, 12, 30)
    result = d.business().add(days=1)
    assert result == d

    d = Date(1899, 1, 2)
    result = d.business().subtract(days=1)
    assert result == d


def test_out_of_range_sentinel_dates_return_self():
    """Sentinel dates outside 1900-2100 return self for every business step.

    Mutation: a zero-day business step snapping an out-of-range date, or
        a one-day step raising.
    Oracle: identity with the sentinel itself, 9999-12-31 and 1800-01-01.
    """
    # Far future sentinel
    d = Date(9999, 12, 31)
    assert d.b.add(days=0) == d
    assert d.b.add(days=1) == d
    assert d.b.subtract(days=0) == d
    assert d.b.subtract(days=1) == d

    # Far past sentinel
    d_past = Date(1800, 1, 1)
    assert d_past.b.add(days=0) == d_past
    assert d_past.b.add(days=1) == d_past
    assert d_past.b.subtract(days=0) == d_past
    assert d_past.b.subtract(days=1) == d_past


def test_boundary_dates_work_normally():
    """Boundary dates (1900, 2100) are in-range and work normally.

    Mutation: an exclusive range check, which treats 1900 or 2100 as out
        of range.
    Oracle: the edge years themselves, 2100-12-31 and 1900-01-01.
    """
    # Last day of valid range
    d = Date(2100, 12, 31)
    result = d.b.subtract(days=0)
    assert result.year == 2100
    assert result.is_business_day()

    # First day of valid range
    d_start = Date(1900, 1, 1)
    result_start = d_start.b.add(days=0)
    assert result_start.year == 1900
    assert result_start.is_business_day()


def test_date_average():
    """Test the average instance method returns the average of two dates.

    Mutation: averaging the year, month and day fields one by one, which
        breaks across a year end.
    Oracle: hand-computed midpoints, one across 2021-12-31.
    """
    result = Date(2022, 1, 1).average(Date(2022, 1, 1))
    assert result == Date(2022, 1, 1)

    result = Date(2022, 1, 1).average(Date(2022, 1, 3))
    assert result == Date(2022, 1, 2)

    result = Date(2022, 1, 1).average(Date(2022, 1, 31))
    assert result == Date(2022, 1, 16)

    result = Date(2021, 12, 31).average(Date(2022, 1, 2))
    assert result == Date(2022, 1, 1)

    assert isinstance(result, Date)


def test_date_fromordinal():
    """Test the fromordinal class method creates correct Date objects.

    Mutation: an ordinal off by one, or a pendulum.Date returned in place
        of a Date.
    Oracle: datetime.date.toordinal - 738156 is 2022-01-01, 738187 is
        2022-02-01 and 737791 is 2021-01-01.
    """
    result = Date.fromordinal(738156)
    assert result == Date(2022, 1, 1)

    result = Date.fromordinal(738187)
    assert result == Date(2022, 2, 1)

    result = Date.fromordinal(737791)
    assert result == Date(2021, 1, 1)

    assert isinstance(result, Date)


def test_date_fromtimestamp():
    """Test the fromtimestamp class method with various timestamps.

    Mutation: a timestamp read in the local zone rather than UTC, which
        dates the midnight-UTC instant to the day before west of UTC.
    Oracle: hand-converted instants - 1641038400 is 2022-01-01 12:00
        UTC, a 2022 date in every zone, and 1643673600 is 2022-02-01
        00:00 UTC.
    """
    timestamp = 1641038400
    result = Date.fromtimestamp(timestamp)
    assert result.year == 2022
    assert result.month == 1
    assert result.day == 1

    timestamp = 1643673600
    result = Date.fromtimestamp(timestamp)
    assert result.year == 2022
    assert result.month == 2
    assert result.day == 1

    assert isinstance(result, Date)


def test_date_nth_of():
    """Test nth_of for finding the nth occurrence of a weekday in a month.

    Mutation: counting occurrences from the first full week, or a fifth
        occurrence overflowing into the next month.
    Oracle: hand-read 2022 calendars.
    """
    base_date = Date(2022, 1, 1)
    result = base_date.nth_of('month', 1, WeekDay.MONDAY)
    assert result == Date(2022, 1, 3)

    base_date = Date(2022, 3, 1)
    result = base_date.nth_of('month', 3, WeekDay.FRIDAY)
    assert result == Date(2022, 3, 18)

    base_date = Date(2022, 5, 1)
    result = base_date.nth_of('month', 5, WeekDay.SUNDAY)
    assert result == Date(2022, 5, 29)

    base_date = Date(2022, 2, 1)
    result = base_date.nth_of('month', 4, WeekDay.MONDAY)
    assert result == Date(2022, 2, 28)

    assert isinstance(result, Date)


def test_date_today():
    """Test the today class method returns current date.

    Mutation: today returning a pendulum.Date, or a date more than a day
        off.
    Oracle: datetime.date.today, within one day to allow for the zone.
    """
    result = Date.today()

    assert isinstance(result, Date)

    today = datetime.date.today()
    diff = abs((today - datetime.date(result.year, result.month, result.day)).days)
    assert diff <= 1


def test_date_to_string():
    """Test the to_string method with various format strings.

    Mutation: to_string mangling a format code on its way to strftime.
    Oracle: hand-written renderings of 2022-01-15.
    """
    d = Date(2022, 1, 15)

    assert d.to_string('%Y-%m-%d') == '2022-01-15'
    assert d.to_string('%m/%d/%Y') == '01/15/2022'
    assert d.to_string('%B %d, %Y') == 'January 15, 2022'
    assert d.to_string('%d-%b-%Y') == '15-Jan-2022'

    result = d.to_string('%-d')
    assert result in {'15', '%#d'}


def test_date_replace():
    """Test the replace method preserves Date type and calendar.

    Mutation: replace returning a pendulum.Date, or dropping _calendar.
    Oracle: get_calendar('NYSE') and hand-written dates.
    """
    d = Date(2022, 1, 15).calendar('NYSE')

    result = d.replace(year=2023)
    assert result == Date(2023, 1, 15)
    assert isinstance(result, Date)
    assert result._calendar == get_calendar('NYSE')

    result = d.replace(month=6)
    assert result == Date(2022, 6, 15)

    result = d.replace(day=1)
    assert result == Date(2022, 1, 1)

    result = d.replace(year=2024, month=12, day=31)
    assert result == Date(2024, 12, 31)


def test_date_closest():
    """Test the closest method returns the closest of two dates.

    Mutation: closest returning the farther date, or always its first
        argument.
    Oracle: hand-counted gaps - 5 days against 10, then 3 against 5,
        with the nearer date in each argument position.
    """
    d = Date(2022, 6, 15)

    d1 = Date(2022, 6, 10)
    d2 = Date(2022, 6, 25)

    result = d.closest(d1, d2)
    assert result == d1
    assert isinstance(result, Date)

    d1 = Date(2022, 6, 18)
    d2 = Date(2022, 6, 10)
    result = d.closest(d1, d2)
    assert result == d1


def test_date_farthest():
    """Test the farthest method returns the farthest of two dates.

    Mutation: farthest returning the nearer date, or always its second
        argument.
    Oracle: hand-counted gaps - 5 days against 10, then 5 against 10.
    """
    d = Date(2022, 6, 15)

    d1 = Date(2022, 6, 10)
    d2 = Date(2022, 6, 25)

    result = d.farthest(d1, d2)
    assert result == d2
    assert isinstance(result, Date)

    d1 = Date(2022, 6, 20)
    d2 = Date(2022, 6, 5)
    result = d.farthest(d1, d2)
    assert result == d2


def test_date_instance_with_pandas_nat():
    """Test Date.instance correctly handles pandas NaT (Not-a-Time).

    Mutation: the pd.isna check dropped, so NaT reaches the field reads.
    Oracle: None, and ValueError 'Empty value' with raise_err.
    """
    result = Date.instance(pd.NaT)
    assert result is None

    with pytest.raises(ValueError, match='Empty value'):
        Date.instance(pd.NaT, raise_err=True)


def test_date_instance_with_numpy_nat():
    """Test Date.instance correctly handles numpy datetime64 NaT.

    Mutation: the pd.isna check dropped, so NaT reaches the datetime64
        cast.
    Oracle: None, and ValueError 'Empty value' with raise_err.
    """
    result = Date.instance(np.datetime64('NaT'))
    assert result is None

    with pytest.raises(ValueError, match='Empty value'):
        Date.instance(np.datetime64('NaT'), raise_err=True)


def test_date_instance_with_pandas_timestamp_valid_dates():
    """Test Date.instance with various valid pandas Timestamps.

    Mutation: a Timestamp converted through UTC, or its date fields
        read off the wrong attributes.
    Oracle: hand-written dates, one a 2020 leap day.
    """
    ts1 = pd.Timestamp('2022-06-15')
    assert Date.instance(ts1) == Date(2022, 6, 15)

    ts2 = pd.Timestamp('2022-12-31 23:59:59')
    assert Date.instance(ts2) == Date(2022, 12, 31)

    ts3 = pd.Timestamp('2020-02-29')
    assert Date.instance(ts3) == Date(2020, 2, 29)


def test_date_instance_with_numpy_datetime64_valid_dates():
    """Test Date.instance with various valid numpy datetime64 objects.

    Mutation: a datetime64 cast at nanosecond unit, whose astype gives
        an int rather than a datetime.
    Oracle: hand-written dates, one a 2020 leap day.
    """
    dt1 = np.datetime64('2022-06-15')
    assert Date.instance(dt1) == Date(2022, 6, 15)

    dt2 = np.datetime64('2022-12-31T23:59:59')
    assert Date.instance(dt2) == Date(2022, 12, 31)

    dt3 = np.datetime64('2020-02-29')
    assert Date.instance(dt3) == Date(2020, 2, 29)


if __name__ == '__main__':
    pytest.main([__file__])
