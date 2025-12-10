import datetime

import numpy as np
import pandas as pd
import pytest

from opendate import EST, UTC, Date, DateTime, Interval, get_calendar


def test_interval_none_validation():
    """Test that Interval raises an error when passed None dates."""
    with pytest.raises(AssertionError):
        Interval(None, None)

    with pytest.raises(AssertionError):
        Interval(Date(2014, 4, 3), None)

    with pytest.raises(AssertionError):
        Interval(None, Date(2014, 4, 3))


def test_business_resets():
    # this should cover each function (essential to test that
    # .business()) deactivated after use
    # paramatrize this test with each function
    d1, d2 = Date(2001, 1, 1), Date(2001, 12, 31)
    assert not d1._business
    assert not d2._business
    Interval(d1, d2).business().days
    assert not d1._business
    assert not d2._business


def test_months_complete():
    """Test months property with complete month intervals."""
    assert Interval(Date(2020, 1, 1), Date(2020, 2, 1)).months == 1.0
    assert Interval(Date(2020, 1, 15), Date(2020, 2, 15)).months == 1.0
    assert Interval(Date(2020, 1, 1), Date(2021, 1, 1)).months == 12.0
    assert Interval(Date(2020, 1, 1), Date(2022, 1, 1)).months == 24.0


def test_months_fractional():
    """Test months property with fractional month intervals."""
    result = Interval(Date(2020, 1, 15), Date(2020, 2, 14)).months
    assert round(result, 2) == 0.97

    result = Interval(Date(2020, 1, 1), Date(2020, 1, 16)).months
    assert round(result, 2) == 0.48

    result = Interval(Date(2020, 1, 10), Date(2020, 2, 20)).months
    assert round(result, 2) == 1.32


def test_months_negative():
    """Test months property with negative intervals."""
    assert Interval(Date(2021, 1, 1), Date(2020, 1, 1)).months == -12.0
    assert Interval(Date(2020, 2, 1), Date(2020, 1, 1)).months == -1.0

    result = Interval(Date(2020, 2, 14), Date(2020, 1, 15)).months
    assert round(result, 2) == -0.97


def test_months_same_date():
    """Test months property when start and end dates are the same."""
    assert Interval(Date(2020, 1, 1), Date(2020, 1, 1)).months == 0.0
    assert Interval(Date(2020, 6, 15), Date(2020, 6, 15)).months == 0.0


def test_months_leap_year():
    """Test months property with leap year dates."""
    result = Interval(Date(2020, 2, 1), Date(2020, 3, 1)).months
    assert result == 1.0

    result = Interval(Date(2020, 2, 15), Date(2020, 3, 15)).months
    assert result == 1.0

    result = Interval(Date(2020, 2, 1), Date(2020, 2, 15)).months
    assert round(result, 2) == 0.48


def test_months_month_boundaries():
    """Test months property at month boundaries."""
    result = Interval(Date(2020, 1, 31), Date(2020, 2, 29)).months
    assert round(result, 2) == 0.94

    result = Interval(Date(2020, 1, 31), Date(2020, 3, 31)).months
    assert result == 2.0

    result = Interval(Date(2020, 3, 31), Date(2020, 4, 30)).months
    assert round(result, 2) == 0.97


def test_months_cross_year():
    """Test months property across year boundaries."""
    result = Interval(Date(2019, 11, 15), Date(2020, 2, 15)).months
    assert result == 3.0

    result = Interval(Date(2019, 12, 20), Date(2020, 1, 10)).months
    assert round(result, 2) == 0.68


@pytest.mark.parametrize(('basis', 'expected'), [
    (0, 42.2139),   # US 30/360
    (1, 42.2142),   # Actual/actual
    (2, 42.8306),   # Actual/360
    (3, 42.2438),   # Actual/365
    (4, 42.2194),   # European 30/360
])
def test_yearfrac_basis(basis, expected):
    """Test yearfrac with different basis values."""
    begdate = Date(1978, 2, 28)
    enddate = Date(2020, 5, 17)

    result = Interval(begdate, enddate).yearfrac(basis)
    assert round(result, 4) == expected

    # Test negative (reverse direction)
    result = Interval(enddate, begdate).yearfrac(basis)
    assert round(result, 4) == -expected


def test_yearfrac_leap_year_edge_case():
    """Test yearfrac with known leap year case (1900 is not a leap year in reality, but Excel has a bug).
    """
    begdate = Date(1900, 1, 1)
    enddate = Date(1900, 12, 1)

    result = Interval(begdate, enddate).yearfrac(4)
    assert round(result, 4) == 0.9167


def test_is_business_day_range():
    """Test is_business_day_range method.
    """
    result = list(Interval(Date(2018, 11, 19), Date(2018, 11, 25)).is_business_day_range())
    assert result == [True, True, True, False, True, False, False]

    result = list(Interval(Date(2021, 11, 22), Date(2021, 11, 28)).is_business_day_range())
    assert result == [True, True, True, False, True, False, False]


def test_interval_range_basic():
    """Test basic range functionality.
    """
    result = next(Interval(Date(2014, 7, 16), Date(2014, 7, 16)).range('days'))
    assert result == Date(2014, 7, 16)

    result = next(Interval(Date(2014, 7, 12), Date(2014, 7, 16)).range('days'))
    assert result == Date(2014, 7, 12)

    result = list(Interval(Date(2014, 7, 12), Date(2014, 7, 16)).range())
    assert len(result) == 5

    result = list(Interval(Date(2014, 7, 16), Date(2014, 7, 20)).range('days'))
    assert len(result) == 5


def test_interval_range_business():
    """Test range with business days.
    """
    result = list(Interval(Date(2014, 7, 3), Date(2014, 7, 5)).b.range('days'))
    assert len(result) == 1

    result = list(Interval(Date(2014, 7, 17), Date(2014, 7, 16)).range('days'))
    assert len(result) == 2

    result = list(Interval(Date(2015, 1, 3), Date(2015, 1, 7)).b.range('days'))
    assert len(result) == 3

    result = list(Interval(Date(2015, 1, 3), Date(2015, 1, 10)).b.range('days'))
    assert len(result) == 5


def test_interval_range_weeks_years():
    """Test range with weeks and years units.
    """
    result = list(Interval(Date(2014, 7, 15), Date(2014, 8, 1)).range('weeks'))
    assert result == [Date(2014, 7, 15), Date(2014, 7, 22), Date(2014, 7, 29)]

    result = list(Interval(Date(2014, 7, 15), Date(2014, 8, 1)).range('years'))
    assert result == [Date(2014, 7, 15)]


def test_interval_days_property():
    """Test days property with and without business mode.
    """
    assert Interval(Date(2018, 9, 6), Date(2018, 9, 10)).days == 4
    assert Interval(Date(2018, 9, 10), Date(2018, 9, 6)).days == -4
    assert Interval(Date(2018, 9, 6), Date(2018, 9, 10)).b.days == 2
    assert Interval(Date(2018, 9, 10), Date(2018, 9, 6)).b.days == -2


def test_interval_years_property():
    """Test years property.
    """
    assert Interval(Date(1978, 2, 28), Date(2020, 5, 17)).years == 42
    assert Interval(Date(2020, 5, 17), Date(1978, 2, 28)).years == -42
    assert Interval(Date(2020, 5, 17), Date(2020, 5, 17)).years == 0
    assert Interval(Date(2020, 5, 17), Date(2021, 5, 16)).years == 0
    assert Interval(Date(2020, 5, 17), Date(2021, 5, 17)).years == 1


def test_interval_quarters_property():
    """Test quarters property.
    """
    assert round(Interval(Date(2020, 1, 1), Date(2020, 2, 16)).quarters, 2) == 0.5
    assert round(Interval(Date(2020, 1, 1), Date(2020, 4, 1)).quarters, 2) == 1.0
    assert round(Interval(Date(2020, 1, 1), Date(2020, 7, 1)).quarters, 2) == 1.99
    assert round(Interval(Date(2020, 1, 1), Date(2020, 8, 1)).quarters, 2) == 2.33


def test_interval_same_date_range():
    """Test range with same start and end date."""
    result = list(Interval(Date(2014, 4, 3), Date(2014, 4, 3)).range('days'))
    assert len(result) == 1
    assert result[0] == Date(2014, 4, 3)


def test_interval_preserves_custom_date_types():
    """Test that Interval preserves custom Date types."""
    d1 = Date(2020, 1, 1)
    d2 = Date(2020, 12, 31)
    interval = Interval(d1, d2)

    assert isinstance(interval.start, Date)
    assert isinstance(interval.end, Date)
    assert type(interval.start).__name__ == 'Date'
    assert type(interval.end).__name__ == 'Date'


def test_interval_preserves_custom_datetime_types():
    """Test that Interval preserves custom DateTime types."""

    dt1 = DateTime(2020, 1, 1, 9, 0, 0, tzinfo=EST)
    dt2 = DateTime(2020, 1, 1, 17, 0, 0, tzinfo=EST)
    interval = Interval(dt1, dt2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert type(interval.start).__name__ == 'DateTime'
    assert type(interval.end).__name__ == 'DateTime'


def test_interval_business_mode_with_custom_types():
    """Test that business mode works with custom Date types preserved."""
    d1 = Date(2018, 9, 6)
    d2 = Date(2018, 9, 10)
    interval = Interval(d1, d2)

    assert type(interval.start).__name__ == 'Date'
    assert type(interval.end).__name__ == 'Date'

    business_days = interval.b.days
    assert business_days == 2


def test_interval_range_returns_custom_types():
    """Test that range() returns custom Date objects."""
    d1 = Date(2020, 1, 1)
    d2 = Date(2020, 1, 5)
    interval = Interval(d1, d2)

    dates = list(interval.range('days'))
    assert all(type(d).__name__ == 'Date' for d in dates)
    assert len(dates) == 5


def test_interval_methods_work_with_custom_types():
    """Test that Interval methods access custom Date attributes correctly."""
    d1 = Date(2020, 1, 1)
    d2 = Date(2020, 2, 1)
    interval = Interval(d1, d2)

    assert hasattr(interval.start, 'is_business_day')
    assert hasattr(interval.end, 'is_business_day')
    assert callable(interval.start.is_business_day)
    assert callable(interval.end.is_business_day)


def test_interval_calendar():
    """Test calendar method sets calendar on interval dates."""
    d1 = Date(2020, 1, 1)
    d2 = Date(2020, 1, 10)
    interval = Interval(d1, d2)

    interval.calendar('NYSE')
    nyse = get_calendar('NYSE')
    assert interval._calendar == nyse
    assert interval._start._calendar == nyse
    assert interval._end._calendar == nyse

    business_days = interval.b.days
    assert business_days == 6


def test_interval_start_of_months():
    """Test Interval.start_of method with month unit."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = interval.start_of('month')
    assert result == [Date(2018, 1, 1), Date(2018, 2, 1), Date(2018, 3, 1), Date(2018, 4, 1)]

    interval = Interval(Date(2018, 4, 30), Date(2018, 7, 30))
    result = interval.start_of('month')
    assert result == [Date(2018, 4, 1), Date(2018, 5, 1), Date(2018, 6, 1), Date(2018, 7, 1)]


def test_interval_start_of_weeks():
    """Test Interval.start_of method with week unit."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = interval.start_of('week')
    assert result == [Date(2018, 1, 1), Date(2018, 1, 8), Date(2018, 1, 15), Date(2018, 1, 22)]


def test_interval_start_of_single_month():
    """Test Interval.start_of with interval within a single month."""
    interval = Interval(Date(2018, 3, 15), Date(2018, 3, 25))
    result = interval.start_of('month')
    assert result == [Date(2018, 3, 1)]


def test_interval_end_of_months():
    """Test Interval.end_of method with month unit."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = interval.end_of('month')
    assert result == [Date(2018, 1, 31), Date(2018, 2, 28), Date(2018, 3, 31), Date(2018, 4, 30)]

    interval = Interval(Date(2018, 4, 30), Date(2018, 7, 30))
    result = interval.end_of('month')
    assert result == [Date(2018, 4, 30), Date(2018, 5, 31), Date(2018, 6, 30), Date(2018, 7, 31)]


def test_interval_end_of_weeks():
    """Test Interval.end_of method with week unit."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = interval.end_of('week')
    assert result == [Date(2018, 1, 7), Date(2018, 1, 14), Date(2018, 1, 21), Date(2018, 1, 28)]


def test_interval_end_of_leap_year():
    """Test Interval.end_of correctly handles February in leap year."""
    interval = Interval(Date(2020, 1, 15), Date(2020, 3, 15))
    result = interval.end_of('month')
    assert result == [Date(2020, 1, 31), Date(2020, 2, 29), Date(2020, 3, 31)]


def test_interval_start_end_with_datetime():
    """Test Interval.start_of and end_of work with DateTime intervals."""
    interval = Interval(DateTime(2018, 1, 5, 10, 0, 0, tzinfo=EST),
                        DateTime(2018, 3, 5, 15, 0, 0, tzinfo=EST))

    start_result = interval.start_of('month')
    assert len(start_result) == 3
    assert all(isinstance(d, DateTime) for d in start_result)

    end_result = interval.end_of('month')
    assert len(end_result) == 3
    assert all(isinstance(d, DateTime) for d in end_result)


def test_interval_business_start_of_month():
    """Test Interval.start_of('month') with business mode."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = interval.b.start_of('month')
    assert result == [Date(2018, 1, 2), Date(2018, 2, 1), Date(2018, 3, 1), Date(2018, 4, 2)]


def test_interval_business_end_of_month():
    """Test Interval.end_of('month') with business mode."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = interval.b.end_of('month')
    assert result == [Date(2018, 1, 31), Date(2018, 2, 28), Date(2018, 3, 29), Date(2018, 4, 30)]


def test_interval_business_start_of_week():
    """Test Interval.start_of('week') with business mode."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = interval.b.start_of('week')
    assert result == [Date(2018, 1, 2), Date(2018, 1, 8), Date(2018, 1, 16), Date(2018, 1, 22)]


def test_interval_business_end_of_week():
    """Test Interval.end_of('week') with business mode."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = interval.b.end_of('week')
    assert result == [Date(2018, 1, 5), Date(2018, 1, 12), Date(2018, 1, 19), Date(2018, 1, 26)]


def test_interval_business_start_of_year():
    """Test Interval.start_of('year') with business mode."""
    interval = Interval(Date(2017, 6, 1), Date(2019, 6, 1))
    result = interval.b.start_of('year')
    assert result == [Date(2017, 1, 3), Date(2018, 1, 2), Date(2019, 1, 2)]


def test_interval_business_end_of_year():
    """Test Interval.end_of('year') with business mode."""
    interval = Interval(Date(2017, 6, 1), Date(2019, 6, 1))
    result = interval.b.end_of('year')
    assert result == [Date(2017, 12, 29), Date(2018, 12, 31), Date(2019, 12, 31)]


def test_interval_business_start_end_preserves_datetime_type():
    """Test that business start_of and end_of preserve DateTime types."""
    interval = Interval(DateTime(2018, 1, 5, 10, 0, 0, tzinfo=EST),
                        DateTime(2018, 3, 5, 15, 0, 0, tzinfo=EST))

    start_result = interval.b.start_of('month')
    assert len(start_result) == 3
    assert all(isinstance(d, DateTime) for d in start_result)

    end_result = interval.b.end_of('month')
    assert len(end_result) == 3
    assert all(isinstance(d, DateTime) for d in end_result)


def test_interval_business_start_of_quarter():
    """Test Interval.start_of('quarter') with business mode."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 12, 31))
    result = interval.b.start_of('quarter')
    assert result == [Date(2018, 1, 2), Date(2018, 4, 2), Date(2018, 7, 2), Date(2018, 10, 1)]


def test_interval_business_end_of_quarter():
    """Test Interval.end_of('quarter') with business mode."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 12, 31))
    result = interval.b.end_of('quarter')
    assert result == [Date(2018, 3, 29), Date(2018, 6, 29), Date(2018, 9, 28), Date(2018, 12, 31)]


def test_interval_business_mode_reset_after_start_of():
    """Test that business mode is properly reset after start_of operation."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    assert interval._business is False
    assert interval._start._business is False
    assert interval._end._business is False

    result = interval.b.start_of('month')

    assert interval._business is False
    assert interval._start._business is False
    assert interval._end._business is False
    assert len(result) == 4


def test_interval_business_mode_reset_after_end_of():
    """Test that business mode is properly reset after end_of operation."""
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    assert interval._business is False
    assert interval._start._business is False
    assert interval._end._business is False

    result = interval.b.end_of('month')

    assert interval._business is False
    assert interval._start._business is False
    assert interval._end._business is False
    assert len(result) == 4


def test_interval_business_start_month_with_holiday_weekend():
    """Test start_of('month') when month starts with holiday followed by weekend."""
    interval = Interval(Date(2021, 12, 15), Date(2022, 1, 15))
    result = interval.b.start_of('month')
    assert result == [Date(2021, 12, 1), Date(2022, 1, 3)]


def test_interval_business_end_month_with_holiday_weekend():
    """Test end_of('month') when month ends with weekend followed by holiday."""
    interval = Interval(Date(2020, 12, 15), Date(2021, 1, 15))
    result = interval.b.end_of('month')
    assert result == [Date(2020, 12, 31), Date(2021, 1, 29)]


def test_interval_business_start_of_single_day_interval():
    """Test start_of with a single-day business interval."""
    date = Date(2018, 3, 15)
    interval = Interval(date, date)
    result = interval.b.start_of('month')
    assert result == [Date(2018, 3, 1)]


def test_interval_business_end_of_single_day_interval():
    """Test end_of with a single-day business interval."""
    date = Date(2018, 3, 15)
    interval = Interval(date, date)
    result = interval.b.end_of('month')
    assert result == [Date(2018, 3, 29)]


def test_interval_business_start_of_with_non_business_start():
    """Test start_of when interval itself starts on non-business day."""
    interval = Interval(Date(2018, 1, 1), Date(2018, 3, 31))
    result = interval.b.start_of('month')
    assert result == [Date(2018, 1, 2), Date(2018, 2, 1), Date(2018, 3, 1)]


def test_interval_business_end_of_with_non_business_end():
    """Test end_of when interval itself ends on non-business day."""
    interval = Interval(Date(2018, 1, 1), Date(2018, 4, 1))
    result = interval.b.end_of('month')
    assert result == [Date(2018, 1, 31), Date(2018, 2, 28), Date(2018, 3, 29), Date(2018, 4, 30)]


def test_interval_business_start_of_day():
    """Test start_of('day') with business mode."""
    interval = Interval(Date(2018, 1, 1), Date(2018, 1, 5))
    result = interval.b.start_of('day')
    assert result == [Date(2018, 1, 2), Date(2018, 1, 3), Date(2018, 1, 4), Date(2018, 1, 5)]


def test_interval_business_end_of_day():
    """Test end_of('day') with business mode."""
    interval = Interval(Date(2018, 1, 1), Date(2018, 1, 5))
    result = interval.b.end_of('day')
    assert result == [Date(2018, 1, 2), Date(2018, 1, 3), Date(2018, 1, 4), Date(2018, 1, 5)]


def test_interval_business_start_of_decade():
    """Test start_of('decade') with business mode."""
    interval = Interval(Date(2008, 6, 15), Date(2022, 6, 15))
    result = interval.b.start_of('decade')
    assert result == [Date(2000, 1, 3), Date(2010, 1, 4), Date(2020, 1, 2)]


def test_interval_business_end_of_decade():
    """Test end_of('decade') with business mode."""
    interval = Interval(Date(2008, 6, 15), Date(2022, 6, 15))
    result = interval.b.end_of('decade')
    assert result == [Date(2009, 12, 31), Date(2019, 12, 31), Date(2029, 12, 31)]


def test_interval_business_start_of_century():
    """Test start_of('century') with business mode."""
    interval = Interval(Date(2010, 6, 15), Date(2015, 6, 15))
    result = interval.b.start_of('century')
    assert result == [Date(2001, 1, 2)]


def test_interval_business_end_of_century():
    """Test end_of('century') with business mode."""
    interval = Interval(Date(2010, 6, 15), Date(2015, 6, 15))
    result = interval.b.end_of('century')
    # Note: 2100-12-31 is a Friday, so it's a valid business day
    assert result == [Date(2100, 12, 31)]


def test_interval_business_all_units_preserve_datetime_type():
    """Test that all unit types preserve DateTime objects in business mode."""
    interval = Interval(DateTime(2018, 1, 1, 10, 0, 0, tzinfo=EST),
                        DateTime(2018, 2, 1, 15, 0, 0, tzinfo=EST))

    for unit in ['day', 'week', 'month', 'quarter', 'year']:
        start_result = interval.b.start_of(unit)
        assert all(isinstance(d, DateTime) for d in start_result)

        end_result = interval.b.end_of(unit)
        assert all(isinstance(d, DateTime) for d in end_result)


def test_interval_range_resets_business_immediately():
    """Test that range() resets business mode immediately when generator is created."""
    interval = Interval(Date(2018, 9, 6), Date(2018, 9, 10))
    assert interval._business is False
    assert interval._start._business is False
    assert interval._end._business is False

    gen = interval.b.range('days')

    assert interval._business is False
    assert interval._start._business is False
    assert interval._end._business is False

    result = list(gen)
    assert len(result) == 3


def test_interval_range_generator_independent_of_later_operations():
    """Test that range() generator works correctly even if other ops are called before consuming."""
    interval = Interval(Date(2018, 9, 6), Date(2018, 9, 10))

    gen = interval.b.range('days')

    _ = interval.days

    result = list(gen)
    assert len(result) == 3
    assert result == [Date(2018, 9, 6), Date(2018, 9, 7), Date(2018, 9, 10)]


def test_interval_multiple_range_generators():
    """Test that multiple range generators can be created and consumed independently."""
    interval = Interval(Date(2018, 9, 6), Date(2018, 9, 10))

    gen1 = interval.b.range('days')
    gen2 = interval.range('days')

    result2 = list(gen2)
    result1 = list(gen1)

    assert len(result1) == 3
    assert len(result2) == 5
    assert result1 == [Date(2018, 9, 6), Date(2018, 9, 7), Date(2018, 9, 10)]
    assert result2 == [Date(2018, 9, 6), Date(2018, 9, 7), Date(2018, 9, 8),
                       Date(2018, 9, 9), Date(2018, 9, 10)]


def test_interval_range_non_days_unit_resets_business():
    """Test that range() with non-days units also resets business mode."""
    interval = Interval(Date(2018, 1, 1), Date(2018, 12, 31))
    assert interval._business is False

    gen = interval.b.range('months')

    assert interval._business is False
    assert interval._start._business is False
    assert interval._end._business is False

    result = list(gen)
    assert len(result) == 12


def test_interval_expect_date_or_datetime_with_date_objects():
    """Test that Interval accepts datetime.date objects and converts them to Date."""
    d1 = datetime.date(2020, 1, 1)
    d2 = datetime.date(2020, 1, 31)

    interval = Interval(d1, d2)

    assert isinstance(interval.start, Date)
    assert isinstance(interval.end, Date)
    assert interval.start == Date(2020, 1, 1)
    assert interval.end == Date(2020, 1, 31)
    assert interval.days == 30


def test_interval_expect_date_or_datetime_with_datetime_objects():
    """Test that Interval accepts datetime.datetime objects and converts them to DateTime."""
    dt1 = datetime.datetime(2020, 1, 1, 9, 30, 0)
    dt2 = datetime.datetime(2020, 1, 1, 16, 0, 0)

    interval = Interval(dt1, dt2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.year == 2020
    assert interval.start.hour == 9
    assert interval.end.hour == 16


def test_interval_expect_date_or_datetime_preserves_date_type():
    """Test that Date objects remain Date objects (not converted to DateTime)."""
    d1 = Date(2020, 1, 1)
    d2 = Date(2020, 1, 31)

    interval = Interval(d1, d2)

    assert type(interval.start).__name__ == 'Date'
    assert type(interval.end).__name__ == 'Date'
    assert not isinstance(interval.start, DateTime)


def test_interval_expect_date_or_datetime_preserves_datetime_type():
    """Test that DateTime objects remain DateTime objects."""
    dt1 = DateTime(2020, 1, 1, 9, 30, 0, tzinfo=UTC)
    dt2 = DateTime(2020, 1, 1, 16, 0, 0, tzinfo=UTC)

    interval = Interval(dt1, dt2)

    assert type(interval.start).__name__ == 'DateTime'
    assert type(interval.end).__name__ == 'DateTime'
    assert interval.start.tzinfo == UTC


def test_interval_expect_date_or_datetime_with_pandas_timestamp():
    """Test that Interval accepts pandas Timestamp and converts to DateTime."""
    ts1 = pd.Timestamp('2020-01-01 09:30:00')
    ts2 = pd.Timestamp('2020-01-01 16:00:00')

    interval = Interval(ts1, ts2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.year == 2020
    assert interval.start.hour == 9
    assert interval.end.hour == 16


def test_interval_expect_date_or_datetime_with_numpy_datetime64():
    """Test that Interval accepts numpy datetime64 and converts to DateTime."""
    np1 = np.datetime64('2020-01-01T09:30:00')
    np2 = np.datetime64('2020-01-01T16:00:00')

    interval = Interval(np1, np2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.year == 2020
    assert interval.start.hour == 9
    assert interval.end.hour == 16


def test_interval_with_pandas_nat_raises_assertion():
    """Test that Interval correctly rejects pandas NaT values."""
    ts1 = pd.Timestamp('2020-01-01 09:30:00')

    # NaT should be rejected (converted to None, then assertion fails)
    with pytest.raises(AssertionError, match='Interval dates cannot be None'):
        Interval(pd.NaT, ts1)

    with pytest.raises(AssertionError, match='Interval dates cannot be None'):
        Interval(ts1, pd.NaT)


def test_interval_with_numpy_nat_raises_assertion():
    """Test that Interval correctly rejects numpy datetime64 NaT values."""
    np1 = np.datetime64('2020-01-01T09:30:00')

    # NaT should be rejected (converted to None, then assertion fails)
    with pytest.raises(AssertionError, match='Interval dates cannot be None'):
        Interval(np.datetime64('NaT'), np1)

    with pytest.raises(AssertionError, match='Interval dates cannot be None'):
        Interval(np1, np.datetime64('NaT'))


def test_interval_expect_date_or_datetime_mixed_types():
    """Test that Interval normalizes mixed Date and DateTime types to DateTime."""
    d = datetime.date(2020, 1, 1)
    dt = datetime.datetime(2020, 1, 31, 16, 0, 0)

    interval = Interval(d, dt)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.year == 2020
    assert interval.start.month == 1
    assert interval.start.day == 1
    assert interval.start.hour == 0
    assert interval.end.year == 2020
    assert interval.end.day == 31
    assert interval.end.hour == 16
    assert interval.start.tzinfo == UTC
    assert interval.end.tzinfo == UTC


def test_interval_expect_date_or_datetime_range_preserves_types():
    """Test that range operations preserve the converted Date/DateTime types."""
    d1 = datetime.date(2020, 1, 1)
    d2 = datetime.date(2020, 1, 5)

    interval = Interval(d1, d2)
    dates = list(interval.range('days'))

    assert all(isinstance(d, Date) for d in dates)
    assert len(dates) == 5

    dt1 = datetime.datetime(2020, 1, 1, 9, 0, 0)
    dt2 = datetime.datetime(2020, 1, 5, 9, 0, 0)

    interval = Interval(dt1, dt2)
    datetimes = list(interval.range('days'))

    assert all(isinstance(dt, DateTime) for dt in datetimes)
    assert len(datetimes) == 5


def test_interval_expect_date_or_datetime_business_operations():
    """Test that business operations work with converted types."""
    d1 = datetime.date(2018, 9, 6)
    d2 = datetime.date(2018, 9, 10)

    interval = Interval(d1, d2)

    assert isinstance(interval.start, Date)
    assert isinstance(interval.end, Date)

    business_days = interval.b.days
    assert business_days == 2

    business_range = list(interval.b.range('days'))
    assert all(isinstance(d, Date) for d in business_range)
    assert len(business_range) == 3


def test_interval_expect_date_or_datetime_with_timezone_aware_datetime():
    """Test that timezone-aware datetime objects are properly handled."""
    dt1 = datetime.datetime(2020, 1, 1, 9, 30, 0, tzinfo=EST)
    dt2 = datetime.datetime(2020, 1, 1, 16, 0, 0, tzinfo=EST)

    interval = Interval(dt1, dt2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.tzinfo == EST
    assert interval.end.tzinfo == EST


def test_interval_mixed_types_preserves_datetime_timezone():
    """Test that when mixing Date and DateTime, the DateTime's timezone is preserved."""
    d = datetime.date(2020, 1, 1)
    dt = datetime.datetime(2020, 1, 31, 16, 0, 0, tzinfo=EST)

    interval = Interval(d, dt)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.tzinfo == EST
    assert interval.end.tzinfo == EST

    interval = Interval(dt, d)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.tzinfo == EST
    assert interval.end.tzinfo == EST


def test_interval_expect_date_or_datetime_yearfrac_with_date():
    """Test that yearfrac works correctly with converted date objects."""
    d1 = datetime.date(1978, 2, 28)
    d2 = datetime.date(2020, 5, 17)

    interval = Interval(d1, d2)

    result = interval.yearfrac(0)
    assert round(result, 4) == 42.2139


def test_interval_expect_date_or_datetime_months_property():
    """Test that months property works with converted date objects."""
    d1 = datetime.date(2020, 1, 1)
    d2 = datetime.date(2020, 2, 1)

    interval = Interval(d1, d2)

    assert interval.months == 1.0


def test_interval_init_decorator_chain():
    """Test that decorators on __init__ properly convert and normalize arguments.

    This test validates the optimization where decorators were moved from __new__
    to __init__ to avoid double-processing. It ensures:
    1. expect_date_or_datetime converts various date-like objects
    2. normalize_date_datetime_pairs handles mixed Date/DateTime inputs
    3. The decorator chain executes in correct order
    """
    d_date = datetime.date(2020, 1, 1)
    d_datetime = datetime.datetime(2020, 1, 31, 16, 0, 0, tzinfo=EST)

    interval = Interval(d_date, d_datetime)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.tzinfo == EST
    assert interval.end.tzinfo == EST
    assert interval.start.hour == 0
    assert interval.end.hour == 16

    pd_timestamp = pd.Timestamp('2020-02-01 09:30:00')
    np_datetime = np.datetime64('2020-02-15T16:00:00')

    interval2 = Interval(pd_timestamp, np_datetime)

    assert isinstance(interval2.start, DateTime)
    assert isinstance(interval2.end, DateTime)
    assert interval2.start.year == 2020
    assert interval2.start.month == 2
    assert interval2.start.day == 1
    assert interval2.end.day == 15


if __name__ == '__main__':
    __import__('pytest').main([__file__])
