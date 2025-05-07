import copy
import datetime
import pickle

import pandas as pd
import pendulum
import pytest
from asserts import assert_equal, assert_true

from date import NYSE, WEEKDAY_SHORTNAME, Date, WeekDay, expect_date


def test_end_of_week():
    """Get the end date of the week."""

    # Regular Monday
    d = Date(2023, 4, 24).end_of('week')
    assert_equal(d, Date(2023, 4, 30))

    # Regular Sunday
    d = Date(2023, 4, 30).end_of('week')
    assert_equal(d, Date(2023, 4, 30))

    # Good Friday
    d = Date(2020, 4, 12).end_of('week')
    assert_equal(d, Date(2020, 4, 12))
    d = Date(2020, 4, 10).end_of('week')
    assert_equal(d, Date(2020, 4, 12))

    d = Date(2020, 4, 10)\
        .business()\
        .end_of('week')
    assert_equal(d, Date(2020, 4, 9))

    d = Date(2020, 4, 9)\
        .end_of('week')\
        .business()\
        .subtract(days=1)
    assert_equal(d, Date(2020, 4, 9))


def test_next_friday():
    """Get next end of week (Friday)."""

    d = Date.instance(datetime.datetime(2018, 10, 8, 0, 0, 0)).next(WeekDay.FRIDAY)
    assert_equal(d, Date(2018, 10, 12))

    d = Date(2018, 10, 12).next(WeekDay.FRIDAY)
    assert_equal(d, Date(2018, 10, 19))


def test_start_of_week():
    """Start of week function (Monday unless not a holiday)."""

    # Regular Monday
    d = Date(2023, 4, 24).start_of('week')
    assert_equal(d, Date(2023, 4, 24))

    # Regular Sunday
    d = Date(2023, 4, 30).start_of('week')
    assert_equal(d, Date(2023, 4, 24))

    # Memorial day 5/25
    d = Date(2020, 5, 25).start_of('week')
    assert_equal(d, Date(2020, 5, 25))
    d = Date(2020, 5, 27).start_of('week')
    assert_equal(d, Date(2020, 5, 25))
    d = Date(2020, 5, 26)\
        .business()\
        .start_of('week')
    assert_equal(d, Date(2020, 5, 26))


def test_end_of_month():
    """End of month"""

    d = Date(2021, 6, 15).end_of('month')
    assert_equal(d, Date(2021, 6, 30))
    d = Date(2021, 6, 30).end_of('month')
    assert_equal(d, Date(2021, 6, 30))

    # Sunday -> Friday
    d =  Date(2023, 4, 30)\
        .business()\
        .end_of('month')
    assert_equal(d, Date(2023, 4, 28))


def test_previous_end_of_month():
    """Previous EOM"""

    d = Date(2021, 5, 30)\
        .start_of('month')\
        .subtract(days=1)
    assert_equal(d, Date(2021, 4, 30))


def test_previous_start_of_month():
    """Previous first of month"""

    d =  Date(2021, 6, 15)\
        .start_of('month')\
        .subtract(days=1)\
        .start_of('month')
    assert_equal(d, Date(2021, 5, 1))

    d = Date(2021, 6, 15)\
        .start_of('month')\
        .subtract(days=1)\
        .business()\
        .start_of('month')
    assert_equal(d, Date(2021, 5, 3))


def test_first_of_year():

    assert_equal(
        Date.today().first_of('year'),
        datetime.date(pendulum.today().year, 1, 1))

    assert_equal(
        Date(2012, 12, 31).first_of('year'),
        datetime.date(2012, 1, 1))


def test_last_of_year():

    d = Date(2022, 4, 2).last_of('year')
    assert_equal(d, Date(2022, 12, 31))


def test_last_of_quarter():
    """Return the quarter start or quarter end of a given date."""

    d = Date(2013, 11, 5).last_of('quarter')
    assert_equal(d, Date(2013, 12, 31))

    d = Date(2016, 3, 31).last_of('quarter')
    assert_equal(d, Date(2016, 3, 31))


def test_first_of_quarter():
    """Return the quarter start or quarter end of a given date."""

    d =  Date(2013, 11, 5).first_of('quarter')
    assert_equal(d, Date(2013, 10, 1))

    d = Date(1999, 1, 19).first_of('quarter')
    assert_equal(d, Date(1999, 1, 1))


def test_last_quarter_date():
    """Return the previous quarter start or quarter end of a given date.
    """

    d = Date(2013, 11, 5)\
        .first_of('quarter')\
        .subtract(days=1)
    assert_equal(d, Date(2013, 9, 30))
    d = Date.instance(datetime.date(2016, 3, 31))\
        .first_of('quarter')\
        .subtract(days=1)
    assert_equal(d, Date(2015, 12, 31))

    d = Date(2013, 11, 5)\
        .first_of('quarter')\
        .subtract(days=1)\
        .first_of('quarter')
    assert_equal(d, Date(2013, 7, 1))
    d = Date.instance(datetime.date(1999, 1, 19))\
        .first_of('quarter')\
        .subtract(days=1)\
        .first_of('quarter')
    assert_equal(d, Date(1998, 10, 1))


def test_loaded_module():
    """We change the module signature. Check that Pendulum still works
    """

    pendulum_date = pendulum.Date(2000, 1, 1)
    d = pendulum_date.add(days=10)
    assert_equal(d, Date(2000, 1, 11))


def test_add():
    # Closed on 12/5/2018 due to George H.W. Bush's death
    i, thedate = 5, datetime.date(2018, 11, 29)
    while i > 0:
        thedate = Date.instance(thedate).b.add(days=1)
        i -= 1
    assert_equal(thedate, Date(2018, 12, 7))

    i, thedate = 5, datetime.date(2021, 11, 17)
    while i > 0:
        thedate = Date.instance(thedate).b.add(days=1)
        i -= 1
    assert_equal(thedate, Date(2021, 11, 24))

    # Infinite date
    d = Date.instance(datetime.date(9999, 12, 31)).b.add(days=1)
    assert_equal(d, Date(9999, 12, 31))

    # In one week (from following doctests)
    d = Date.instance(datetime.date(2018, 11, 29)).b.add(days=5)
    assert_equal(d, Date(2018, 12, 7))
    d = Date(2021, 11, 17).b.add(days=5)
    assert_equal(d, Date(2021, 11, 24))

    # Test reverse direction
    d = Date.instance(datetime.date(2018, 11, 29)).b.subtract(days=-5)
    assert_equal(d, Date(2018, 12, 7))
    d = Date(2021, 11, 17).b.subtract(days=-5)
    assert_equal(d, Date(2021, 11, 24))


def test_subtract():

    # Closed on 12/5/2018 due to George H.W. Bush's death
    d = Date(2018, 12, 7).b.subtract(days=5)
    assert_equal(d, Date(2018, 11, 29))
    d = Date(2021, 11, 24).b.subtract(days=5)
    assert_equal(d, Date(2021, 11, 17))

    # One week ago (from following doctests)
    d = Date(2018, 12, 7).b.subtract(days=5)
    assert_equal(d, Date(2018, 11, 29))
    d = Date(2021, 11, 24).subtract(days=7)
    assert_equal(d, Date(2021, 11, 17))
    d = Date(2018, 12, 7).b.subtract(days=5)
    assert_equal(d, Date(2018, 11, 29))
    d = Date(2021, 11, 24).subtract(days=7)
    assert_equal(d, Date(2021, 11, 17))

    # Test reverse direction
    d = Date(2018, 12, 7).b.add(days=-5)
    assert_equal(d, Date(2018, 11, 29))
    d = Date(2021, 11, 24).add(days=-7)
    assert_equal(d, Date(2021, 11, 17))
    d = Date(2018, 12, 7).b.add(days=-5)
    assert_equal(d, Date(2018, 11, 29))
    d = Date(2021, 11, 24).add(days=-7)
    assert_equal(d, Date(2021, 11, 17))


def test_set_entity():

    d = Date(2000, 1, 1).entity(NYSE).b.add(days=10)
    assert_equal(d, Date(2000, 1, 14))


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

    # cross test between parsing and adding/subtracting negative
    # business days
    assert_equal(Date.parse('T-3b'), Date.today().b.subtract(days=3))
    assert_equal(Date.parse('T-3b'), Date.today().b.add(days=-3))
    assert_equal(Date.parse('T+3b'), Date.today().b.subtract(days=-3))
    assert_equal(Date.parse('T+3b'), Date.today().b.subtract(days=-3))

    assert_equal(Date.parse('P'), Date.today().b.subtract(days=1))
    assert_equal(Date.parse('P'), Date.today().b.add(days=-1))
    assert_equal(Date.parse('P-3b'), Date.today().b.add(days=-1).b.subtract(days=3))
    assert_equal(Date.parse('P-3b'), Date.today().b.subtract(days=1).b.add(days=-3))
    assert_equal(Date.parse('P+3b'), Date.today().b.add(days=-1).b.subtract(days=-3))
    assert_equal(Date.parse('P+3b'), Date.today().b.subtract(days=1).b.subtract(days=-3))

    assert_equal(Date.parse('01/11/19'), Date(2019, 1, 11))
    assert_equal(Date.parse('01/11/19'), Date(2019, 1, 11))
    assert_equal(Date.parse('01/15/20'), Date(2020, 1, 15))
    assert_equal(Date.parse('01/15/21'), Date(2021, 1, 15))
    assert_equal(Date.parse('01/15/22'), Date(2022, 1, 15))

    assert_equal(None, Date.parse('100.264400'))


def test_copy():

    d = pendulum.Date(2022, 1, 1)
    assert_equal(copy.copy(d), d)

    d = Date(2022, 1, 1)
    assert_equal(copy.copy(d), d)


def test_deepcopy():

    d = pendulum.Date(2022, 1, 1)
    assert_equal(copy.deepcopy(d), d)

    d = Date(2022, 1, 1)
    assert_equal(copy.deepcopy(d), d)


def test_pickle():

    d = Date(2022, 1, 1)

    with open('date.pkl', 'wb') as f:
        pickle.dump(d, f)
    with open('date.pkl', 'rb') as f:
        d_ = pickle.load(f)

    assert_equal(d, d_)


def test_expects():

    @expect_date
    def func(args):
        return args

    p = pendulum.Date(2022, 1, 1)
    d = Date(2022, 1, 1)
    df = pd.DataFrame([['foo', 1], ['bar', 2]], columns=['name', 'value'])

    assert_equal(func(p), d)
    assert_equal(func((p, p)), [d, d])
    assert_equal(func(((p, p), p)), [[d, d], d])
    assert_true(isinstance(func((df, p))[0], pd.DataFrame))


def test_isoweek():
    """Test the isoweek method returns correct ISO week numbers."""
    assert_equal(Date(2023, 1, 2).isoweek(), 1)
    assert_equal(Date(2023, 4, 27).isoweek(), 17)
    assert_equal(Date(2023, 12, 31).isoweek(), 52)
    assert_equal(Date(2023, 1, 1).isoweek(), 52)  # Belongs to previous year's week


def test_lookback():
    """Test lookback functionality with different units."""
    test_date = Date(2018, 12, 7)

    assert_equal(test_date.lookback('last'), Date(2018, 12, 6))
    assert_equal(test_date.lookback('day'), Date(2018, 12, 6))
    assert_equal(test_date.lookback('week'), Date(2018, 11, 30))
    assert_equal(test_date.lookback('month'), Date(2018, 11, 7))

    # Test with business lookback
    assert_equal(test_date.b.lookback('last'), Date(2018, 12, 6))
    assert_equal(test_date.b.lookback('month'), Date(2018, 11, 7))


def test_third_wednesday():
    """Test third_wednesday class method and its alias."""
    # Test class method
    assert_equal(Date.third_wednesday(2022, 6), Date(2022, 6, 15))
    assert_equal(Date.third_wednesday(2023, 3), Date(2023, 3, 15))
    assert_equal(Date.third_wednesday(2022, 12), Date(2022, 12, 21))
    assert_equal(Date.third_wednesday(2023, 6), Date(2023, 6, 21))


def test_nearest_start_and_end_of_month():
    """Test nearest_start_of_month and nearest_end_of_month methods."""
    # Test nearest_start_of_month
    assert_equal(Date(2015, 1, 1).nearest_start_of_month(), Date(2015, 1, 1))
    assert_equal(Date(2015, 1, 15).nearest_start_of_month(), Date(2015, 1, 1))
    assert_equal(Date(2015, 1, 16).nearest_start_of_month(), Date(2015, 2, 1))
    assert_equal(Date(2015, 1, 31).nearest_start_of_month(), Date(2015, 2, 1))

    # Test with business days
    assert_equal(Date(2015, 1, 15).b.nearest_start_of_month(), Date(2015, 1, 2))
    assert_equal(Date(2015, 1, 31).b.nearest_start_of_month(), Date(2015, 2, 2))

    # Test nearest_end_of_month
    assert_equal(Date(2015, 1, 1).nearest_end_of_month(), Date(2014, 12, 31))
    assert_equal(Date(2015, 1, 15).nearest_end_of_month(), Date(2014, 12, 31))
    assert_equal(Date(2015, 1, 16).nearest_end_of_month(), Date(2015, 1, 31))
    assert_equal(Date(2015, 1, 31).nearest_end_of_month(), Date(2015, 1, 31))

    # Test with business days
    assert_equal(Date(2015, 1, 15).b.nearest_end_of_month(), Date(2014, 12, 31))
    assert_equal(Date(2015, 1, 31).b.nearest_end_of_month(), Date(2015, 1, 30))


def test_weekday_or_previous_friday():
    """Test weekday_or_previous_friday method."""
    # Test with weekday
    assert_equal(Date(2019, 10, 4).weekday_or_previous_friday(), Date(2019, 10, 4))  # Friday
    assert_equal(Date(2019, 10, 3).weekday_or_previous_friday(), Date(2019, 10, 3))  # Thursday

    # Test with weekend
    assert_equal(Date(2019, 10, 5).weekday_or_previous_friday(), Date(2019, 10, 4))  # Saturday -> Friday
    assert_equal(Date(2019, 10, 6).weekday_or_previous_friday(), Date(2019, 10, 4))  # Sunday -> Friday


def test_next_relative_date_of_week_by_day():
    """Test next_relative_date_of_week_by_day method."""
    # Test when target day is in the future
    assert_equal(Date(2020, 5, 18).next_relative_date_of_week_by_day('SU'), Date(2020, 5, 24))

    # Test when target day is the current day
    assert_equal(Date(2020, 5, 24).next_relative_date_of_week_by_day('SU'), Date(2020, 5, 24))

    # Test with different days
    assert_equal(Date(2020, 5, 18).next_relative_date_of_week_by_day('TU'), Date(2020, 5, 19))
    assert_equal(Date(2020, 5, 18).next_relative_date_of_week_by_day('WE'), Date(2020, 5, 20))


def test_business_methods():
    """Test business day related methods."""
    # Test is_business_day
    assert_equal(Date(2021, 4, 19).is_business_day(), True)  # Monday
    assert_equal(Date(2021, 4, 17).is_business_day(), False)  # Saturday
    assert_equal(Date(2021, 1, 18).is_business_day(), False)  # MLK Day
    assert_equal(Date(2021, 11, 25).is_business_day(), False)  # Thanksgiving

    # Test business_open (same as is_business_day)
    assert_equal(Date(2021, 4, 19).business_open(), True)
    assert_equal(Date(2021, 4, 17).business_open(), False)

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


def test_date_average():
    """Test the average instance method returns the average of two dates."""
    # Test with equal dates
    result = Date(2022, 1, 1).average(Date(2022, 1, 1))
    assert_equal(result, Date(2022, 1, 1))

    # Test with dates one day apart
    result = Date(2022, 1, 1).average(Date(2022, 1, 3))
    assert_equal(result, Date(2022, 1, 2))

    # Test with dates further apart
    result = Date(2022, 1, 1).average(Date(2022, 1, 31))
    assert_equal(result, Date(2022, 1, 16))

    # Test with dates in different years
    result = Date(2021, 12, 31).average(Date(2022, 1, 2))
    assert_equal(result, Date(2022, 1, 1))

    # Verify result is Date instance
    assert isinstance(result, Date)


def test_date_fromordinal():
    """Test the fromordinal class method creates correct Date objects."""
    # January 1, 2022 is the 738156th day since January 1, 1
    result = Date.fromordinal(738156)
    assert_equal(result, Date(2022, 1, 1))

    # Test another date
    result = Date.fromordinal(738187)  # February 1, 2022
    assert_equal(result, Date(2022, 2, 1))

    # Test date in different year
    result = Date.fromordinal(737791)  # January 1, 2021
    assert_equal(result, Date(2021, 1, 1))

    # Verify result is Date instance
    assert isinstance(result, Date)


def test_date_fromtimestamp():
    """Test the fromtimestamp class method with various timestamps."""
    # Test with timestamp for 2022-01-01
    # Using a timestamp that's safely in 2022 in any timezone
    timestamp = 1641038400  # 2022-01-01 12:00:00 UTC
    result = Date.fromtimestamp(timestamp)
    assert_equal(result.year, 2022)
    assert_equal(result.month, 1)
    assert_equal(result.day, 1)

    # Test with another timestamp
    timestamp = 1643673600  # 2022-02-01 UTC
    result = Date.fromtimestamp(timestamp)
    assert_equal(result.year, 2022)
    assert_equal(result.month, 2)
    assert_equal(result.day, 1)

    # Verify result is Date instance
    assert isinstance(result, Date)


def test_date_nth_of():
    """Test the nth_of instance method for finding nth occurrence of weekday in month."""
    # Test finding the 1st Monday of January 2022
    base_date = Date(2022, 1, 1)
    result = base_date.nth_of('month', 1, WeekDay.MONDAY)
    assert_equal(result, Date(2022, 1, 3))

    # Test finding the 3rd Friday of March 2022
    base_date = Date(2022, 3, 1)
    result = base_date.nth_of('month', 3, WeekDay.FRIDAY)
    assert_equal(result, Date(2022, 3, 18))

    # Test finding the 5th Sunday of May 2022 (which exists)
    base_date = Date(2022, 5, 1)
    result = base_date.nth_of('month', 5, WeekDay.SUNDAY)
    assert_equal(result, Date(2022, 5, 29))

    # Test with last day of month case
    base_date = Date(2022, 2, 1)
    result = base_date.nth_of('month', 4, WeekDay.MONDAY)
    assert_equal(result, Date(2022, 2, 28))

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


if __name__ == '__main__':
    pytest.main([__file__])
