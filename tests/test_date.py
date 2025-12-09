import copy
import datetime
import pathlib
import pickle

import numpy as np
import pandas as pd
import pendulum
import pytest

from date import WEEKDAY_SHORTNAME, Date, WeekDay, expect_date, get_calendar


def test_end_of_week():
    """Get the end date of the week."""

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
    """Get next end of week (Friday)."""

    d = Date.instance(datetime.datetime(2018, 10, 8, 0, 0, 0)).next(WeekDay.FRIDAY)
    assert d == Date(2018, 10, 12)

    d = Date(2018, 10, 12).next(WeekDay.FRIDAY)
    assert d == Date(2018, 10, 19)


def test_start_of_week():
    """Start of week function (Monday unless not a holiday)."""

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
    """End of month"""

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
    """Previous EOM"""

    d = Date(2021, 5, 30)\
        .start_of('month')\
        .subtract(days=1)
    assert d == Date(2021, 4, 30)


def test_previous_start_of_month():
    """Previous first of month"""

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

    assert Date.today().first_of('year') == datetime.date(pendulum.today().year, 1, 1)

    assert Date(2012, 12, 31).first_of('year') == datetime.date(2012, 1, 1)


def test_last_of_year():

    d = Date(2022, 4, 2).last_of('year')
    assert d == Date(2022, 12, 31)


def test_last_of_quarter():
    """Return the quarter start or quarter end of a given date."""

    d = Date(2013, 11, 5).last_of('quarter')
    assert d == Date(2013, 12, 31)

    d = Date(2016, 3, 31).last_of('quarter')
    assert d == Date(2016, 3, 31)


def test_first_of_quarter():
    """Return the quarter start or quarter end of a given date."""

    d =  Date(2013, 11, 5).first_of('quarter')
    assert d == Date(2013, 10, 1)

    d = Date(1999, 1, 19).first_of('quarter')
    assert d == Date(1999, 1, 1)


def test_last_quarter_date():
    """Return the previous quarter start or quarter end of a given date.
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
    """We change the module signature. Check that Pendulum still works
    """

    pendulum_date = pendulum.Date(2000, 1, 1)
    d = pendulum_date.add(days=10)
    assert d == Date(2000, 1, 11)


def test_add():
    # Closed on 12/5/2018 due to George H.W. Bush's death
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

    # Out-of-range date returns self unchanged (no exception)
    d = Date.instance(datetime.date(9999, 12, 31))
    result = d.b.add(days=1)
    assert result == d

    # In one week (from following doctests)
    d = Date.instance(datetime.date(2018, 11, 29)).b.add(days=5)
    assert d == Date(2018, 12, 7)
    d = Date(2021, 11, 17).b.add(days=5)
    assert d == Date(2021, 11, 24)

    # Test reverse direction
    d = Date.instance(datetime.date(2018, 11, 29)).b.subtract(days=-5)
    assert d == Date(2018, 12, 7)
    d = Date(2021, 11, 17).b.subtract(days=-5)
    assert d == Date(2021, 11, 24)


def test_subtract():

    # Closed on 12/5/2018 due to George H.W. Bush's death
    d = Date(2018, 12, 7).b.subtract(days=5)
    assert d == Date(2018, 11, 29)
    d = Date(2021, 11, 24).b.subtract(days=5)
    assert d == Date(2021, 11, 17)

    # One week ago (from following doctests)
    d = Date(2018, 12, 7).b.subtract(days=5)
    assert d == Date(2018, 11, 29)
    d = Date(2021, 11, 24).subtract(days=7)
    assert d == Date(2021, 11, 17)
    d = Date(2018, 12, 7).b.subtract(days=5)
    assert d == Date(2018, 11, 29)
    d = Date(2021, 11, 24).subtract(days=7)
    assert d == Date(2021, 11, 17)

    # Test reverse direction
    d = Date(2018, 12, 7).b.add(days=-5)
    assert d == Date(2018, 11, 29)
    d = Date(2021, 11, 24).add(days=-7)
    assert d == Date(2021, 11, 17)
    d = Date(2018, 12, 7).b.add(days=-5)
    assert d == Date(2018, 11, 29)
    d = Date(2021, 11, 24).add(days=-7)
    assert d == Date(2021, 11, 17)


def test_set_calendar():
    """Test setting calendar on Date."""
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
    """Test Date.parse with various input formats."""
    # Business day calculations
    assert Date.parse('T-3b') == Date.today().b.subtract(days=3)
    assert Date.parse('T-3b') == Date.today().b.add(days=-3)
    assert Date.parse('T+3b') == Date.today().b.subtract(days=-3)
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


@pytest.mark.parametrize(('input_str', 'expected'), [
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
    """Test Date.parse with various date format strings."""
    assert Date.parse(input_str) == expected


def test_parse_date_no_year():
    """Test m/d format (no year - uses current year)."""
    result = Date.parse('01/15')
    assert result.month == 1
    assert result.day == 15


def test_parse_special_strings():
    """Test Date.parse with special string keywords."""
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
    """Test Date.parse error handling behavior."""
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


def test_copy():

    d = pendulum.Date(2022, 1, 1)
    assert copy.copy(d) == d

    d = Date(2022, 1, 1)
    assert copy.copy(d) == d


def test_deepcopy():

    d = pendulum.Date(2022, 1, 1)
    assert copy.deepcopy(d) == d

    d = Date(2022, 1, 1)
    assert copy.deepcopy(d) == d


def test_pickle(tmp_path):
    """Test pickle serialization and deserialization of Date objects."""
    d = Date(2022, 1, 1)

    pickle_file = tmp_path / 'date.pkl'
    with pathlib.Path(pickle_file).open('wb') as f:
        pickle.dump(d, f)
    with pathlib.Path(pickle_file).open('rb') as f:
        d_ = pickle.load(f)

    assert d == d_


def test_expects():

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


@pytest.mark.parametrize(('date', 'expected_week'), [
    (Date(2023, 1, 2), 1),
    (Date(2023, 4, 27), 17),
    (Date(2023, 12, 31), 52),
    (Date(2023, 1, 1), 52),  # Belongs to previous year's week
])
def test_isoweek(date, expected_week):
    """Test the isoweek method returns correct ISO week numbers."""
    assert date.isoweek() == expected_week


def test_lookback():
    """Test lookback functionality with different units."""
    test_date = Date(2018, 12, 7)

    assert test_date.lookback('last') == Date(2018, 12, 6)
    assert test_date.lookback('day') == Date(2018, 12, 6)
    assert test_date.lookback('week') == Date(2018, 11, 30)
    assert test_date.lookback('month') == Date(2018, 11, 7)

    # Test with business lookback
    assert test_date.b.lookback('last') == Date(2018, 12, 6)
    assert test_date.b.lookback('month') == Date(2018, 11, 7)


@pytest.mark.parametrize(('year', 'month', 'expected'), [
    (2022, 6, Date(2022, 6, 15)),
    (2023, 3, Date(2023, 3, 15)),
    (2022, 12, Date(2022, 12, 21)),
    (2023, 6, Date(2023, 6, 21)),
])
def test_third_wednesday(year, month, expected):
    """Test third_wednesday class method."""
    assert Date.third_wednesday(year, month) == expected


def test_nearest_start_and_end_of_month():
    """Test nearest_start_of_month and nearest_end_of_month methods."""
    # Test nearest_start_of_month
    assert Date(2015, 1, 1).nearest_start_of_month() == Date(2015, 1, 1)
    assert Date(2015, 1, 15).nearest_start_of_month() == Date(2015, 1, 1)
    assert Date(2015, 1, 16).nearest_start_of_month() == Date(2015, 2, 1)
    assert Date(2015, 1, 31).nearest_start_of_month() == Date(2015, 2, 1)

    # Test with business days
    assert Date(2015, 1, 15).b.nearest_start_of_month() == Date(2015, 1, 2)
    assert Date(2015, 1, 31).b.nearest_start_of_month() == Date(2015, 2, 2)

    # Test nearest_end_of_month
    assert Date(2015, 1, 1).nearest_end_of_month() == Date(2014, 12, 31)
    assert Date(2015, 1, 15).nearest_end_of_month() == Date(2014, 12, 31)
    assert Date(2015, 1, 16).nearest_end_of_month() == Date(2015, 1, 31)
    assert Date(2015, 1, 31).nearest_end_of_month() == Date(2015, 1, 31)

    # Test with business days
    assert Date(2015, 1, 15).b.nearest_end_of_month() == Date(2014, 12, 31)
    assert Date(2015, 1, 31).b.nearest_end_of_month() == Date(2015, 1, 30)


def test_nearest_start_of_month_business_snapping():
    """Test that nearest_start_of_month snaps (not snap+add) in business mode."""
    # Early in month (day <= 15), start is business day
    # March 1, 2024 is Friday (business day)
    d = Date(2024, 3, 10).b.nearest_start_of_month()
    assert d == Date(2024, 3, 1), f'Expected March 1, got {d}'

    # Early in month, start is weekend
    # December 1, 2024 is Sunday → December 2 is Monday
    d = Date(2024, 12, 10).b.nearest_start_of_month()
    assert d == Date(2024, 12, 2), f'Expected December 2, got {d}'

    # Late in month (day > 15), next month start is business day
    # April 1, 2024 is Monday (business day)
    d = Date(2024, 3, 20).b.nearest_start_of_month()
    assert d == Date(2024, 4, 1), f'Expected April 1, got {d}'

    # Late in month, next month start is weekend
    # December 1, 2024 is Sunday → December 2 is Monday
    d = Date(2024, 11, 20).b.nearest_start_of_month()
    assert d == Date(2024, 12, 2), f'Expected December 2, got {d}'


def test_nearest_end_of_month_business_snapping():
    """Test that nearest_end_of_month snaps (not snap+subtract) in business mode."""
    # Early in month (day <= 15), prev month end is business day
    # Feb 29, 2024 is Thursday (business day)
    d = Date(2024, 3, 10).b.nearest_end_of_month()
    assert d == Date(2024, 2, 29), f'Expected Feb 29, got {d}'

    # Early in month, prev month end is weekend
    # June 30, 2024 is Sunday → June 28 is Friday
    d = Date(2024, 7, 10).b.nearest_end_of_month()
    assert d == Date(2024, 6, 28), f'Expected June 28, got {d}'

    # Late in month (day > 15), current month end is weekend + holiday
    # March 31, 2024 is Sunday, March 29 is Good Friday (holiday)
    # → March 28 is Thursday
    d = Date(2024, 3, 20).b.nearest_end_of_month()
    assert d == Date(2024, 3, 28), f'Expected March 28, got {d}'


def test_weekday_or_previous_friday():
    """Test weekday_or_previous_friday method."""
    # Test with weekday
    assert Date(2019, 10, 4).weekday_or_previous_friday() == Date(2019, 10, 4)  # Friday
    assert Date(2019, 10, 3).weekday_or_previous_friday() == Date(2019, 10, 3)  # Thursday

    # Test with weekend
    assert Date(2019, 10, 5).weekday_or_previous_friday() == Date(2019, 10, 4)  # Saturday -> Friday
    assert Date(2019, 10, 6).weekday_or_previous_friday() == Date(2019, 10, 4)  # Sunday -> Friday


def test_next_relative_date_of_week_by_day():
    """Test next_relative_date_of_week_by_day method."""
    # Test when target day is in the future
    assert Date(2020, 5, 18).next_relative_date_of_week_by_day('SU') == Date(2020, 5, 24)

    # Test when target day is the current day
    assert Date(2020, 5, 24).next_relative_date_of_week_by_day('SU') == Date(2020, 5, 24)

    # Test with different days
    assert Date(2020, 5, 18).next_relative_date_of_week_by_day('TU') == Date(2020, 5, 19)
    assert Date(2020, 5, 18).next_relative_date_of_week_by_day('WE') == Date(2020, 5, 20)


def test_business_methods():
    """Test business day related methods."""
    # Test is_business_day
    assert Date(2021, 4, 19).is_business_day()  # Monday
    assert not Date(2021, 4, 17).is_business_day()  # Saturday
    assert not Date(2021, 1, 18).is_business_day()  # MLK Day
    assert not Date(2021, 11, 25).is_business_day()  # Thanksgiving

    # Test business_open (same as is_business_day)
    assert Date(2021, 4, 19).business_open()
    assert not Date(2021, 4, 17).business_open()

    # Test business_hours
    # We can't assert exact times due to potential timezone differences, but we can check existence
    open_time, close_time = Date(2023, 1, 5).business_hours()
    assert open_time is not None
    assert close_time is not None
    assert open_time.hour == 9
    assert open_time.minute == 30

    # Test holiday with no business hours
    open_time, close_time = Date(2024, 5, 27).business_hours()  # Memorial day
    assert open_time is None
    assert close_time is None


def test_out_of_range_date_noop():
    """Dates outside 1900-2100: is_business_day returns False, operations return self."""
    # Year > 2100: is_business_day returns False
    d = Date(9999, 12, 31)
    assert d.is_business_day() is False

    d = Date(2101, 1, 1)
    assert d.is_business_day() is False

    # Year < 1900: is_business_day returns False
    d = Date(1899, 12, 31)
    assert d.is_business_day() is False

    # business().add() on far future date returns self unchanged
    d = Date(9999, 12, 30)
    result = d.business().add(days=1)
    assert result == d

    # business().subtract() on far past date returns self unchanged
    d = Date(1899, 1, 2)
    result = d.business().subtract(days=1)
    assert result == d


def test_date_average():
    """Test the average instance method returns the average of two dates."""
    # Test with equal dates
    result = Date(2022, 1, 1).average(Date(2022, 1, 1))
    assert result == Date(2022, 1, 1)

    # Test with dates one day apart
    result = Date(2022, 1, 1).average(Date(2022, 1, 3))
    assert result == Date(2022, 1, 2)

    # Test with dates further apart
    result = Date(2022, 1, 1).average(Date(2022, 1, 31))
    assert result == Date(2022, 1, 16)

    # Test with dates in different years
    result = Date(2021, 12, 31).average(Date(2022, 1, 2))
    assert result == Date(2022, 1, 1)

    # Verify result is Date instance
    assert isinstance(result, Date)


def test_date_fromordinal():
    """Test the fromordinal class method creates correct Date objects."""
    # January 1, 2022 is the 738156th day since January 1, 1
    result = Date.fromordinal(738156)
    assert result == Date(2022, 1, 1)

    # Test another date
    result = Date.fromordinal(738187)  # February 1, 2022
    assert result == Date(2022, 2, 1)

    # Test date in different year
    result = Date.fromordinal(737791)  # January 1, 2021
    assert result == Date(2021, 1, 1)

    # Verify result is Date instance
    assert isinstance(result, Date)


def test_date_fromtimestamp():
    """Test the fromtimestamp class method with various timestamps."""
    # Test with timestamp for 2022-01-01
    # Using a timestamp that's safely in 2022 in any timezone
    timestamp = 1641038400  # 2022-01-01 12:00:00 UTC
    result = Date.fromtimestamp(timestamp)
    assert result.year == 2022
    assert result.month == 1
    assert result.day == 1

    # Test with another timestamp
    timestamp = 1643673600  # 2022-02-01 UTC
    result = Date.fromtimestamp(timestamp)
    assert result.year == 2022
    assert result.month == 2
    assert result.day == 1

    # Verify result is Date instance
    assert isinstance(result, Date)


def test_date_nth_of():
    """Test the nth_of instance method for finding nth occurrence of weekday in month."""
    # Test finding the 1st Monday of January 2022
    base_date = Date(2022, 1, 1)
    result = base_date.nth_of('month', 1, WeekDay.MONDAY)
    assert result == Date(2022, 1, 3)

    # Test finding the 3rd Friday of March 2022
    base_date = Date(2022, 3, 1)
    result = base_date.nth_of('month', 3, WeekDay.FRIDAY)
    assert result == Date(2022, 3, 18)

    # Test finding the 5th Sunday of May 2022 (which exists)
    base_date = Date(2022, 5, 1)
    result = base_date.nth_of('month', 5, WeekDay.SUNDAY)
    assert result == Date(2022, 5, 29)

    # Test with last day of month case
    base_date = Date(2022, 2, 1)
    result = base_date.nth_of('month', 4, WeekDay.MONDAY)
    assert result == Date(2022, 2, 28)

    # Verify result is Date instance
    assert isinstance(result, Date)


def test_date_today():
    """Test the today class method returns current date."""
    # Since the actual date will vary, we just check basic properties
    result = Date.today()

    # Test that it's a Date instance
    assert isinstance(result, Date)

    # Test that it's close to today (within 1 day, to handle timezone differences)
    import datetime as dt
    today = dt.date.today()
    diff = abs((today - dt.date(result.year, result.month, result.day)).days)
    assert diff <= 1


def test_date_to_string():
    """Test the to_string method with various format strings."""
    d = Date(2022, 1, 15)

    assert d.to_string('%Y-%m-%d') == '2022-01-15'
    assert d.to_string('%m/%d/%Y') == '01/15/2022'
    assert d.to_string('%B %d, %Y') == 'January 15, 2022'
    assert d.to_string('%d-%b-%Y') == '15-Jan-2022'

    # Test platform-specific format (%-d on Unix, %#d on Windows)
    result = d.to_string('%-d')
    assert result in {'15', '%#d'}  # Handles both platforms


def test_date_replace():
    """Test the replace method preserves Date type and calendar."""
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
    """Test the closest method returns the closest of two dates."""
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
    """Test the farthest method returns the farthest of two dates."""
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
    """Test Date.instance correctly handles pandas NaT (Not-a-Time)."""
    # Test with raise_err=False (default)
    result = Date.instance(pd.NaT)
    assert result is None

    # Test with raise_err=True
    with pytest.raises(ValueError, match='Empty value'):
        Date.instance(pd.NaT, raise_err=True)


def test_date_instance_with_numpy_nat():
    """Test Date.instance correctly handles numpy datetime64 NaT."""
    # Test with raise_err=False (default)
    result = Date.instance(np.datetime64('NaT'))
    assert result is None

    # Test with raise_err=True
    with pytest.raises(ValueError, match='Empty value'):
        Date.instance(np.datetime64('NaT'), raise_err=True)


def test_date_instance_with_pandas_timestamp_valid_dates():
    """Test Date.instance with various valid pandas Timestamps."""
    # Test with different date formats
    ts1 = pd.Timestamp('2022-06-15')
    assert Date.instance(ts1) == Date(2022, 6, 15)

    ts2 = pd.Timestamp('2022-12-31 23:59:59')
    assert Date.instance(ts2) == Date(2022, 12, 31)

    ts3 = pd.Timestamp('2020-02-29')  # Leap year
    assert Date.instance(ts3) == Date(2020, 2, 29)


def test_date_instance_with_numpy_datetime64_valid_dates():
    """Test Date.instance with various valid numpy datetime64 objects."""
    # Test with different formats
    dt1 = np.datetime64('2022-06-15')
    assert Date.instance(dt1) == Date(2022, 6, 15)

    dt2 = np.datetime64('2022-12-31T23:59:59')
    assert Date.instance(dt2) == Date(2022, 12, 31)

    dt3 = np.datetime64('2020-02-29')  # Leap year
    assert Date.instance(dt3) == Date(2020, 2, 29)


if __name__ == '__main__':
    pytest.main([__file__])
