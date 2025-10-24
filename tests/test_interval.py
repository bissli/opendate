import pytest

from date import Date, Interval


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


def test_yearfrac_basis_0():
    """Test yearfrac with basis 0 (US 30/360).
    """
    begdate = Date(1978, 2, 28)
    enddate = Date(2020, 5, 17)

    result = Interval(begdate, enddate).yearfrac(0)
    assert round(result, 4) == 42.2139

    result = Interval(enddate, begdate).yearfrac(0)
    assert round(result, 4) == -42.2139


def test_yearfrac_basis_1():
    """Test yearfrac with basis 1 (Actual/actual).
    """
    begdate = Date(1978, 2, 28)
    enddate = Date(2020, 5, 17)

    result = Interval(begdate, enddate).yearfrac(1)
    assert round(result, 4) == 42.2142


def test_yearfrac_basis_2():
    """Test yearfrac with basis 2 (Actual/360).
    """
    begdate = Date(1978, 2, 28)
    enddate = Date(2020, 5, 17)

    result = Interval(begdate, enddate).yearfrac(2)
    assert round(result, 4) == 42.8306


def test_yearfrac_basis_3():
    """Test yearfrac with basis 3 (Actual/365).
    """
    begdate = Date(1978, 2, 28)
    enddate = Date(2020, 5, 17)

    result = Interval(begdate, enddate).yearfrac(3)
    assert round(result, 4) == 42.2438


def test_yearfrac_basis_4():
    """Test yearfrac with basis 4 (European 30/360).
    """
    begdate = Date(1978, 2, 28)
    enddate = Date(2020, 5, 17)

    result = Interval(begdate, enddate).yearfrac(4)
    assert round(result, 4) == 42.2194

    result = Interval(enddate, begdate).yearfrac(4)
    assert round(result, 4) == -42.2194


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
    from date import EST, DateTime

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


def test_interval_entity():
    """Test entity method sets entity on interval dates."""
    from date import NYSE

    d1 = Date(2020, 1, 1)
    d2 = Date(2020, 1, 10)
    interval = Interval(d1, d2)

    interval.entity(NYSE)
    assert interval._entity == NYSE
    assert interval._start._entity == NYSE
    assert interval._end._entity == NYSE

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
    from date import EST, DateTime

    interval = Interval(DateTime(2018, 1, 5, 10, 0, 0, tzinfo=EST),
                       DateTime(2018, 3, 5, 15, 0, 0, tzinfo=EST))
    
    start_result = interval.start_of('month')
    assert len(start_result) == 3
    assert all(isinstance(d, DateTime) for d in start_result)
    
    end_result = interval.end_of('month')
    assert len(end_result) == 3
    assert all(isinstance(d, DateTime) for d in end_result)


if __name__ == '__main__':
    __import__('pytest').main([__file__])
