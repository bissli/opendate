import datetime

import numpy as np
import pandas as pd
import pytest
from opendate import EST, UTC, Date, DateTime, Interval, get_calendar


def test_interval_none_validation():
    """Test that Interval raises an error when passed None dates.

    Mutation: the None check reading only begdate.
    Oracle: the AssertionError Interval documents for a None endpoint.
    """
    with pytest.raises(AssertionError):
        Interval(None, None)

    with pytest.raises(AssertionError):
        Interval(Date(2014, 4, 3), None)

    with pytest.raises(AssertionError):
        Interval(None, Date(2014, 4, 3))


def test_business_resets():
    """Verify days turns business mode off on the caller's endpoints.

    Mutation: reset_business dropped from days, which leaves both Date
        objects in business mode.
    Oracle: the endpoints' _business flags, False before the call.
    """
    d1, d2 = Date(2001, 1, 1), Date(2001, 12, 31)
    assert not d1._business
    assert not d2._business
    Interval(d1, d2).business().days
    assert not d1._business
    assert not d2._business


def test_months_complete():
    """Test months property with complete month intervals.

    Mutation: the year term dropped from the whole-month count.
    Oracle: hand-counted calendar months.
    """
    assert Interval(Date(2020, 1, 1), Date(2020, 2, 1)).months == 1.0
    assert Interval(Date(2020, 1, 15), Date(2020, 2, 15)).months == 1.0
    assert Interval(Date(2020, 1, 1), Date(2021, 1, 1)).months == 12.0
    assert Interval(Date(2020, 1, 1), Date(2022, 1, 1)).months == 24.0


def test_months_fractional():
    """Test months property with fractional month intervals.

    Mutation: the fraction taken over the end month's length, or over a
        flat 30 days.
    Oracle: hand-computed fractions of January's 31 days, to 2dp.
    """
    result = Interval(Date(2020, 1, 15), Date(2020, 2, 14)).months
    assert round(result, 2) == 0.97

    result = Interval(Date(2020, 1, 1), Date(2020, 1, 16)).months
    assert round(result, 2) == 0.48

    result = Interval(Date(2020, 1, 10), Date(2020, 2, 20)).months
    assert round(result, 2) == 1.32


def test_months_negative():
    """Test months property with negative intervals.

    Mutation: the sign of a reversed interval lost.
    Oracle: the forward values, negated.
    """
    assert Interval(Date(2021, 1, 1), Date(2020, 1, 1)).months == -12.0
    assert Interval(Date(2020, 2, 1), Date(2020, 1, 1)).months == -1.0

    result = Interval(Date(2020, 2, 14), Date(2020, 1, 15)).months
    assert round(result, 2) == -0.97


def test_months_leap_year():
    """Test months property with leap year dates.

    Mutation: a fixed month-length table with February at 28 days.
    Oracle: hand-computed 14/29 for 2020-02-01 to 2020-02-15.
    """
    result = Interval(Date(2020, 2, 1), Date(2020, 3, 1)).months
    assert result == 1.0

    result = Interval(Date(2020, 2, 15), Date(2020, 3, 15)).months
    assert result == 1.0

    result = Interval(Date(2020, 2, 1), Date(2020, 2, 15)).months
    assert round(result, 2) == 0.48


def test_months_month_boundaries():
    """Test months property at month boundaries.

    Mutation: the fraction taken over the end month's length, or a
        month-end to month-end span counted as whole months.
    Oracle: hand-computed fractions over the start month's 31 days.
    """
    result = Interval(Date(2020, 1, 31), Date(2020, 2, 29)).months
    assert round(result, 2) == 0.94

    result = Interval(Date(2020, 1, 31), Date(2020, 3, 31)).months
    assert result == 2.0

    result = Interval(Date(2020, 3, 31), Date(2020, 4, 30)).months
    assert round(result, 2) == 0.97


def test_months_cross_year():
    """Test months property across year boundaries.

    Mutation: the year term dropped, so the month difference goes
        negative across a year end.
    Oracle: hand-counted months.
    """
    result = Interval(Date(2019, 11, 15), Date(2020, 2, 15)).months
    assert result == 3.0

    result = Interval(Date(2019, 12, 20), Date(2020, 1, 10)).months
    assert round(result, 2) == 0.68


@pytest.mark.parametrize(
    ('basis', 'expected'),
    [
        (0, 42.2139),   # 30/360 US
        (1, 42.2154),   # ACT/ACT ISDA
        (2, 42.8306),   # ACT/360
        (3, 42.2438),   # ACT/365 Fixed
        (4, 42.2194),   # 30E/360
        (5, 42.2149),   # ACT/365.25
        (6, 42.2194),   # 30/360 Bond Basis
        (7, 42.2139),   # 30E/360 ISDA
        (8, 42.2137),   # ACT/365 No Leap
        ])
def test_yearfrac_basis(basis, expected):
    """Verify each basis over one long span, forward and reversed.

    Mutation: a basis dispatched to a neighbor's arithmetic, or the sign
        lost on a reversed interval.
    Oracle: QuantLib year fractions for 1978-02-28 -> 2020-05-17, 4dp.
    """
    begdate = Date(1978, 2, 28)
    enddate = Date(2020, 5, 17)

    result = Interval(begdate, enddate).yearfrac(basis)
    assert round(result, 4) == expected

    result = Interval(enddate, begdate).yearfrac(basis)
    assert round(result, 4) == -expected


def test_yearfrac_leap_year_edge_case():
    """Verify 30E/360 before 1901, outside QuantLib's date domain.

    Mutation: a day rule that needs a year after 1900, such as a
        QuantLib-backed or ordinal-bounded path.
    Oracle: hand-computed 330/360.
    """
    begdate = Date(1900, 1, 1)
    enddate = Date(1900, 12, 1)

    result = Interval(begdate, enddate).yearfrac(4)
    assert round(result, 4) == 0.9167


def test_is_business_day_range():
    """Test is_business_day_range method.

    Mutation: the flag reading the weekday alone, which misses
        Thanksgiving; or the walk leaving out the last day.
    Oracle: NYSE closed on Thanksgiving, 2018-11-22 and 2021-11-25.
    """
    result = list(
        Interval(Date(2018, 11, 19), Date(2018, 11, 25)).is_business_day_range())
    assert result == [True, True, True, False, True, False, False]

    result = list(
        Interval(Date(2021, 11, 22), Date(2021, 11, 28)).is_business_day_range())
    assert result == [True, True, True, False, True, False, False]


def test_interval_range_basic():
    """Test basic range functionality.

    Mutation: the end left out of the walk, so a one-day interval yields
        nothing and a five-day span yields four.
    Oracle: hand-counted inclusive day spans.
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

    Mutation: the business filter ignoring holidays, or a reversed
        interval yielding no days.
    Oracle: hand-counted NYSE sessions, with 2014-07-04 a holiday.
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

    Mutation: the unit ignored, so every unit steps by days.
    Oracle: hand-listed weekly steps from 2014-07-15.
    """
    result = list(Interval(Date(2014, 7, 15), Date(2014, 8, 1)).range('weeks'))
    assert result == [Date(2014, 7, 15), Date(2014, 7, 22), Date(2014, 7, 29)]

    result = list(Interval(Date(2014, 7, 15), Date(2014, 8, 1)).range('years'))
    assert result == [Date(2014, 7, 15)]


def test_interval_days_property():
    """Test days property with and without business mode.

    Mutation: the business count keeping the end day, or the sign of a
        reversed interval lost.
    Oracle: hand-counted days, 2018-09-06 a Thursday and 09-10 a Monday.
    """
    assert Interval(Date(2018, 9, 6), Date(2018, 9, 10)).days == 4
    assert Interval(Date(2018, 9, 10), Date(2018, 9, 6)).days == -4
    assert Interval(Date(2018, 9, 6), Date(2018, 9, 10)).b.days == 2
    assert Interval(Date(2018, 9, 10), Date(2018, 9, 6)).b.days == -2


def test_interval_years_property():
    """Test years property.

    Mutation: the year difference taken without the anniversary check,
        or a reversed interval floored to -43.
    Oracle: hand-counted anniversaries.
    """
    assert Interval(Date(1978, 2, 28), Date(2020, 5, 17)).years == 42
    assert Interval(Date(2020, 5, 17), Date(1978, 2, 28)).years == -42
    assert Interval(Date(2020, 5, 17), Date(2020, 5, 17)).years == 0
    assert Interval(Date(2020, 5, 17), Date(2021, 5, 16)).years == 0
    assert Interval(Date(2020, 5, 17), Date(2021, 5, 17)).years == 1


def test_interval_quarters_property():
    """Test quarters property.

    Mutation: a 360-day year in the formula.
    Oracle: hand-computed 4 * days / 365, to 2dp.
    """
    assert round(Interval(Date(2020, 1, 1), Date(2020, 2, 16)).quarters, 2) == 0.5
    assert round(Interval(Date(2020, 1, 1), Date(2020, 4, 1)).quarters, 2) == 1.0
    assert round(Interval(Date(2020, 1, 1), Date(2020, 7, 1)).quarters, 2) == 1.99
    assert round(Interval(Date(2020, 1, 1), Date(2020, 8, 1)).quarters, 2) == 2.33


def test_interval_same_date_range():
    """Test range with same start and end date.

    Mutation: a one-day interval yielding its date twice, once as start
        and once as end.
    Oracle: a one-day span holds one date.
    """
    result = list(Interval(Date(2014, 4, 3), Date(2014, 4, 3)).range('days'))
    assert len(result) == 1
    assert result[0] == Date(2014, 4, 3)


def test_interval_preserves_custom_date_types():
    """Test that Interval preserves custom Date types.

    Mutation: the endpoints stored as pendulum.Date, which lacks the
        business methods.
    Oracle: the opendate Date class of the inputs.
    """
    d1 = Date(2020, 1, 1)
    d2 = Date(2020, 12, 31)
    interval = Interval(d1, d2)

    assert isinstance(interval.start, Date)
    assert isinstance(interval.end, Date)
    assert type(interval.start).__name__ == 'Date'
    assert type(interval.end).__name__ == 'Date'


def test_interval_preserves_custom_datetime_types():
    """Test that Interval preserves custom DateTime types.

    Mutation: the endpoints stored as pendulum.DateTime.
    Oracle: the opendate DateTime class of the inputs.
    """

    dt1 = DateTime(2020, 1, 1, 9, 0, 0, tzinfo=EST)
    dt2 = DateTime(2020, 1, 1, 17, 0, 0, tzinfo=EST)
    interval = Interval(dt1, dt2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert type(interval.start).__name__ == 'DateTime'
    assert type(interval.end).__name__ == 'DateTime'


def test_interval_calendar():
    """Test calendar method sets calendar on interval dates.

    Mutation: the calendar set on the interval alone, leaving the
        endpoints on their old calendar.
    Oracle: get_calendar('NYSE'), and 6 NYSE sessions from 2020-01-01 up
        to and excluding 2020-01-10.
    """
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
    """Test Interval.start_of method with month unit.

    Mutation: the first start clipped to the interval start.
    Oracle: hand-listed month starts.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = interval.start_of('month')
    assert result == [
        Date(2018, 1, 1),
        Date(2018, 2, 1),
        Date(2018, 3, 1),
        Date(2018, 4, 1),
        ]

    interval = Interval(Date(2018, 4, 30), Date(2018, 7, 30))
    result = interval.start_of('month')
    assert result == [
        Date(2018, 4, 1),
        Date(2018, 5, 1),
        Date(2018, 6, 1),
        Date(2018, 7, 1),
        ]


def test_interval_start_of_weeks():
    """Test Interval.start_of method with week unit.

    Mutation: weeks starting on Sunday.
    Oracle: weeks start on Monday, and 2018-01-01 is a Monday.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = interval.start_of('week')
    assert result == [
        Date(2018, 1, 1),
        Date(2018, 1, 8),
        Date(2018, 1, 15),
        Date(2018, 1, 22),
        ]


def test_interval_start_of_single_month():
    """Test Interval.start_of with interval within a single month.

    Mutation: the walk starting at the first period start on or after the
        interval start, which finds none inside 2018-03-15..25.
    Oracle: the start of March 2018.
    """
    interval = Interval(Date(2018, 3, 15), Date(2018, 3, 25))
    result = interval.start_of('month')
    assert result == [Date(2018, 3, 1)]


def test_interval_end_of_months():
    """Test Interval.end_of method with month unit.

    Mutation: the last end clipped to the interval end.
    Oracle: hand-listed month ends.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = interval.end_of('month')
    assert result == [
        Date(2018, 1, 31),
        Date(2018, 2, 28),
        Date(2018, 3, 31),
        Date(2018, 4, 30),
        ]

    interval = Interval(Date(2018, 4, 30), Date(2018, 7, 30))
    result = interval.end_of('month')
    assert result == [
        Date(2018, 4, 30),
        Date(2018, 5, 31),
        Date(2018, 6, 30),
        Date(2018, 7, 31),
        ]


def test_interval_end_of_weeks():
    """Test Interval.end_of method with week unit.

    Mutation: weeks ending on Saturday.
    Oracle: weeks end on Sunday, and 2018-01-07 is a Sunday.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = interval.end_of('week')
    assert result == [
        Date(2018, 1, 7),
        Date(2018, 1, 14),
        Date(2018, 1, 21),
        Date(2018, 1, 28),
        ]


def test_interval_end_of_leap_year():
    """Test Interval.end_of correctly handles February in leap year.

    Mutation: February ending on the 28th in every year.
    Oracle: 2020-02-29.
    """
    interval = Interval(Date(2020, 1, 15), Date(2020, 3, 15))
    result = interval.end_of('month')
    assert result == [Date(2020, 1, 31), Date(2020, 2, 29), Date(2020, 3, 31)]


def test_interval_start_end_with_datetime():
    """Test Interval.start_of and end_of work with DateTime intervals.

    Mutation: a period start or end built as a Date from a DateTime.
    Oracle: the DateTime class of the inputs, and 3 months overlapped.
    """
    interval = Interval(
        DateTime(2018, 1, 5, 10, 0, 0, tzinfo=EST),
        DateTime(2018, 3, 5, 15, 0, 0, tzinfo=EST))

    start_result = interval.start_of('month')
    assert len(start_result) == 3
    assert all(isinstance(d, DateTime) for d in start_result)

    end_result = interval.end_of('month')
    assert len(end_result) == 3
    assert all(isinstance(d, DateTime) for d in end_result)


def test_interval_business_start_of_month():
    """Test Interval.start_of('month') with business mode.

    Mutation: a non-business start moved to the previous business day,
        or New Year's Day taken as a business day.
    Oracle: NYSE 2018, closed 01-01, and 04-01 a Sunday.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = interval.b.start_of('month')
    assert result == [
        Date(2018, 1, 2),
        Date(2018, 2, 1),
        Date(2018, 3, 1),
        Date(2018, 4, 2),
        ]


def test_interval_business_end_of_month():
    """Test Interval.end_of('month') with business mode.

    Mutation: a non-business end moved to the next business day, or Good
        Friday taken as a business day.
    Oracle: NYSE 2018, closed Good Friday 03-30, and 03-31 a Saturday.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = interval.b.end_of('month')
    assert result == [
        Date(2018, 1, 31),
        Date(2018, 2, 28),
        Date(2018, 3, 29),
        Date(2018, 4, 30),
        ]


def test_interval_business_start_of_week():
    """Test Interval.start_of('week') with business mode.

    Mutation: the business adjustment skipping weekends but not holidays.
    Oracle: NYSE 2018, closed 01-01 and Martin Luther King Day 01-15.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = interval.b.start_of('week')
    assert result == [
        Date(2018, 1, 2),
        Date(2018, 1, 8),
        Date(2018, 1, 16),
        Date(2018, 1, 22),
        ]


def test_interval_business_end_of_week():
    """Test Interval.end_of('week') with business mode.

    Mutation: a Sunday week end moved forward to Monday.
    Oracle: the Friday before each Sunday week end.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = interval.b.end_of('week')
    assert result == [
        Date(2018, 1, 5),
        Date(2018, 1, 12),
        Date(2018, 1, 19),
        Date(2018, 1, 26),
        ]


def test_interval_business_start_of_year():
    """Test Interval.start_of('year') with business mode.

    Mutation: an observed holiday taken as a business day.
    Oracle: NYSE closed 2017-01-02 for New Year's Day observed.
    """
    interval = Interval(Date(2017, 6, 1), Date(2019, 6, 1))
    result = interval.b.start_of('year')
    assert result == [Date(2017, 1, 3), Date(2018, 1, 2), Date(2019, 1, 2)]


def test_interval_business_end_of_year():
    """Test Interval.end_of('year') with business mode.

    Mutation: a non-business year end moved forward into January.
    Oracle: 2017-12-31 a Sunday, so the last session is 12-29.
    """
    interval = Interval(Date(2017, 6, 1), Date(2019, 6, 1))
    result = interval.b.end_of('year')
    assert result == [Date(2017, 12, 29), Date(2018, 12, 31), Date(2019, 12, 31)]


def test_interval_business_start_end_preserves_datetime_type():
    """Test that business start_of and end_of preserve DateTime types.

    Mutation: the business adjustment returning a Date for a DateTime.
    Oracle: the DateTime class of the inputs, and 3 months overlapped.
    """
    interval = Interval(
        DateTime(2018, 1, 5, 10, 0, 0, tzinfo=EST),
        DateTime(2018, 3, 5, 15, 0, 0, tzinfo=EST))

    start_result = interval.b.start_of('month')
    assert len(start_result) == 3
    assert all(isinstance(d, DateTime) for d in start_result)

    end_result = interval.b.end_of('month')
    assert len(end_result) == 3
    assert all(isinstance(d, DateTime) for d in end_result)


def test_interval_business_start_of_quarter():
    """Test Interval.start_of('quarter') with business mode.

    Mutation: advance stepping three months from the adjusted start
        without returning to the quarter start, so 07-02 steps to 10-02.
    Oracle: NYSE 2018, with 04-01 and 07-01 on Sundays.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 12, 31))
    result = interval.b.start_of('quarter')
    assert result == [
        Date(2018, 1, 2),
        Date(2018, 4, 2),
        Date(2018, 7, 2),
        Date(2018, 10, 1),
        ]


def test_interval_business_end_of_quarter():
    """Test Interval.end_of('quarter') with business mode.

    Mutation: the quarter end month off by one, or Good Friday taken as
        a business day.
    Oracle: NYSE 2018, closed Good Friday 03-30, with 06-30 and 09-30 on
        a weekend.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 12, 31))
    result = interval.b.end_of('quarter')
    assert result == [
        Date(2018, 3, 29),
        Date(2018, 6, 29),
        Date(2018, 9, 28),
        Date(2018, 12, 31),
        ]


def test_interval_business_mode_reset_after_start_of():
    """Test that business mode is properly reset after start_of operation.

    Mutation: reset_business dropped from start_of.
    Oracle: the _business flags, False before the call.
    """
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
    """Test that business mode is properly reset after end_of operation.

    Mutation: reset_business dropped from end_of.
    Oracle: the _business flags, False before the call.
    """
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
    """Test start_of('month') when January 2022 opens on a weekend.

    Mutation: the business adjustment stepping one day only, which lands
        on Sunday 2022-01-02.
    Oracle: NYSE's first 2022 session, 01-03.
    """
    interval = Interval(Date(2021, 12, 15), Date(2022, 1, 15))
    result = interval.b.start_of('month')
    assert result == [Date(2021, 12, 1), Date(2022, 1, 3)]


def test_interval_business_end_month_with_holiday_weekend():
    """Test end_of('month') when month ends with weekend followed by holiday.

    Mutation: the business adjustment stepping one day only, which lands
        on Saturday 2021-01-30.
    Oracle: 2021-01-31 a Sunday, so the last session is 01-29.
    """
    interval = Interval(Date(2020, 12, 15), Date(2021, 1, 15))
    result = interval.b.end_of('month')
    assert result == [Date(2020, 12, 31), Date(2021, 1, 29)]


def test_interval_business_start_of_single_day_interval():
    """Test start_of with a single-day business interval.

    Mutation: the walk starting at the interval start, which yields
        2018-03-15 or nothing.
    Oracle: 2018-03-01, a Thursday session.
    """
    date = Date(2018, 3, 15)
    interval = Interval(date, date)
    result = interval.b.start_of('month')
    assert result == [Date(2018, 3, 1)]


def test_interval_business_end_of_single_day_interval():
    """Test end_of with a single-day business interval.

    Mutation: Good Friday taken as a business day.
    Oracle: NYSE closed Good Friday 2018-03-30, and 03-31 a Saturday.
    """
    date = Date(2018, 3, 15)
    interval = Interval(date, date)
    result = interval.b.end_of('month')
    assert result == [Date(2018, 3, 29)]


def test_interval_business_start_of_with_non_business_start():
    """Test start_of when interval itself starts on non-business day.

    Mutation: New Year's Day taken as a business day.
    Oracle: NYSE closed 2018-01-01.
    """
    interval = Interval(Date(2018, 1, 1), Date(2018, 3, 31))
    result = interval.b.start_of('month')
    assert result == [Date(2018, 1, 2), Date(2018, 2, 1), Date(2018, 3, 1)]


def test_interval_business_end_of_with_non_business_end():
    """Test end_of when interval itself ends on non-business day.

    Mutation: the April period dropped because the interval ends on
        Sunday 2018-04-01.
    Oracle: NYSE 2018 month-end sessions, Good Friday 03-30 closed.
    """
    interval = Interval(Date(2018, 1, 1), Date(2018, 4, 1))
    result = interval.b.end_of('month')
    assert result == [
        Date(2018, 1, 31),
        Date(2018, 2, 28),
        Date(2018, 3, 29),
        Date(2018, 4, 30),
        ]


def test_interval_business_start_of_day():
    """Test start_of('day') with business mode.

    Mutation: New Year's Day taken as a business day.
    Oracle: NYSE closed 2018-01-01.
    """
    interval = Interval(Date(2018, 1, 1), Date(2018, 1, 5))
    result = interval.b.start_of('day')
    assert result == [
        Date(2018, 1, 2),
        Date(2018, 1, 3),
        Date(2018, 1, 4),
        Date(2018, 1, 5),
        ]


def test_interval_business_end_of_day():
    """Test end_of('day') with business mode.

    Mutation: New Year's Day taken as a business day.
    Oracle: NYSE closed 2018-01-01.
    """
    interval = Interval(Date(2018, 1, 1), Date(2018, 1, 5))
    result = interval.b.end_of('day')
    assert result == [
        Date(2018, 1, 2),
        Date(2018, 1, 3),
        Date(2018, 1, 4),
        Date(2018, 1, 5),
        ]


def test_interval_business_start_of_decade():
    """Test start_of('decade') with business mode.

    Mutation: the decade case dropped from the unit handlers, so advance
        calls add(decades=1).
    Oracle: first NYSE sessions of 2000, 2010 and 2020.
    """
    interval = Interval(Date(2008, 6, 15), Date(2022, 6, 15))
    result = interval.b.start_of('decade')
    assert result == [Date(2000, 1, 3), Date(2010, 1, 4), Date(2020, 1, 2)]


def test_interval_business_end_of_decade():
    """Test end_of('decade') with business mode.

    Mutation: the decade case dropped from the unit handlers, so advance
        calls add(decades=1).
    Oracle: last NYSE sessions of 2009, 2019 and 2029.
    """
    interval = Interval(Date(2008, 6, 15), Date(2022, 6, 15))
    result = interval.b.end_of('decade')
    assert result == [Date(2009, 12, 31), Date(2019, 12, 31), Date(2029, 12, 31)]


def test_interval_business_start_of_century():
    """Test start_of('century') with business mode.

    Mutation: the century case dropped from the unit handlers, so advance
        calls add(centurys=1).
    Oracle: pendulum's century starting 2001-01-01, an NYSE holiday.
    """
    interval = Interval(Date(2010, 6, 15), Date(2015, 6, 15))
    result = interval.b.start_of('century')
    assert result == [Date(2001, 1, 2)]


def test_interval_business_end_of_century():
    """Test end_of('century') with business mode.

    Mutation: the century case dropped from the unit handlers, so advance
        calls add(centurys=1).
    Oracle: pendulum's century ending 2100-12-31, a Friday session.
    """
    interval = Interval(Date(2010, 6, 15), Date(2015, 6, 15))
    result = interval.b.end_of('century')
    assert result == [Date(2100, 12, 31)]


def test_interval_business_all_units_preserve_datetime_type():
    """Test that all unit types preserve DateTime objects in business mode.

    Mutation: one unit's handler, such as the quarter helpers, returning
        a Date for a DateTime.
    Oracle: the DateTime class of the inputs.
    """
    interval = Interval(
        DateTime(2018, 1, 1, 10, 0, 0, tzinfo=EST),
        DateTime(2018, 2, 1, 15, 0, 0, tzinfo=EST))

    for unit in ['day', 'week', 'month', 'quarter', 'year']:
        start_result = interval.b.start_of(unit)
        assert all(isinstance(d, DateTime) for d in start_result)

        end_result = interval.b.end_of(unit)
        assert all(isinstance(d, DateTime) for d in end_result)


def test_interval_range_resets_business_immediately():
    """Test that range() resets business mode as soon as it returns.

    Mutation: the reset deferred until the generator runs out, or the
        generator reading business mode after the reset, which yields
        all 5 days.
    Oracle: the _business flags, False before the call, and 3 sessions
        from 2018-09-06 to 09-10.
    """
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
    """Test that a range() generator keeps its mode across later calls.

    Mutation: the generator reading self._business when consumed, after
        days has reset it.
    Oracle: the 3 NYSE sessions from 2018-09-06 to 09-10.
    """
    interval = Interval(Date(2018, 9, 6), Date(2018, 9, 10))

    gen = interval.b.range('days')

    _ = interval.days

    result = list(gen)
    assert len(result) == 3
    assert result == [Date(2018, 9, 6), Date(2018, 9, 7), Date(2018, 9, 10)]


def test_interval_multiple_range_generators():
    """Test that multiple range generators are consumed independently.

    Mutation: generators sharing one business flag, so the plain
        generator skips weekends or the business one keeps them.
    Oracle: hand-listed days, 2018-09-08 and 09-09 a weekend.
    """
    interval = Interval(Date(2018, 9, 6), Date(2018, 9, 10))

    gen1 = interval.b.range('days')
    gen2 = interval.range('days')

    result2 = list(gen2)
    result1 = list(gen1)

    assert len(result1) == 3
    assert len(result2) == 5
    assert result1 == [Date(2018, 9, 6), Date(2018, 9, 7), Date(2018, 9, 10)]
    assert result2 == [
        Date(2018, 9, 6),
        Date(2018, 9, 7),
        Date(2018, 9, 8),
        Date(2018, 9, 9),
        Date(2018, 9, 10),
        ]


def test_interval_range_non_days_unit_resets_business():
    """Test that range() with non-days units also resets business mode.

    Mutation: the reset applied on the 'days' path alone.
    Oracle: the _business flags, False before the call, and 12 month
        steps in 2018.
    """
    interval = Interval(Date(2018, 1, 1), Date(2018, 12, 31))
    assert interval._business is False

    gen = interval.b.range('months')

    assert interval._business is False
    assert interval._start._business is False
    assert interval._end._business is False

    result = list(gen)
    assert len(result) == 12


def test_interval_expect_date_or_datetime_with_date_objects():
    """Test that Interval converts datetime.date objects to Date.

    Mutation: a datetime.date endpoint left unconverted.
    Oracle: the opendate Date class, and 30 days in the span.
    """
    d1 = datetime.date(2020, 1, 1)
    d2 = datetime.date(2020, 1, 31)

    interval = Interval(d1, d2)

    assert isinstance(interval.start, Date)
    assert isinstance(interval.end, Date)
    assert interval.start == Date(2020, 1, 1)
    assert interval.end == Date(2020, 1, 31)
    assert interval.days == 30


def test_interval_expect_date_or_datetime_with_datetime_objects():
    """Test that Interval converts datetime.datetime objects to DateTime.

    Mutation: a datetime.datetime endpoint cut to a Date, losing its time.
    Oracle: the input hours, 9 and 16.
    """
    dt1 = datetime.datetime(2020, 1, 1, 9, 30, 0)
    dt2 = datetime.datetime(2020, 1, 1, 16, 0, 0)

    interval = Interval(dt1, dt2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.year == 2020
    assert interval.start.hour == 9
    assert interval.end.hour == 16


def test_interval_expect_date_or_datetime_preserves_datetime_type():
    """Test that DateTime objects remain DateTime objects.

    Mutation: a DateTime endpoint rebuilt in the local timezone.
    Oracle: the UTC tzinfo of the inputs.
    """
    dt1 = DateTime(2020, 1, 1, 9, 30, 0, tzinfo=UTC)
    dt2 = DateTime(2020, 1, 1, 16, 0, 0, tzinfo=UTC)

    interval = Interval(dt1, dt2)

    assert type(interval.start).__name__ == 'DateTime'
    assert type(interval.end).__name__ == 'DateTime'
    assert interval.start.tzinfo == UTC


def test_interval_expect_date_or_datetime_with_pandas_timestamp():
    """Test that Interval accepts pandas Timestamp and converts to DateTime.

    Mutation: a pandas Timestamp endpoint left unconverted.
    Oracle: the opendate DateTime class, and the input hours.
    """
    ts1 = pd.Timestamp('2020-01-01 09:30:00')
    ts2 = pd.Timestamp('2020-01-01 16:00:00')

    interval = Interval(ts1, ts2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.year == 2020
    assert interval.start.hour == 9
    assert interval.end.hour == 16


def test_interval_expect_date_or_datetime_with_numpy_datetime64():
    """Test that Interval accepts numpy datetime64 and converts to DateTime.

    Mutation: a numpy datetime64 endpoint left unconverted, or cut to a
        Date.
    Oracle: the opendate DateTime class, and the input hours.
    """
    np1 = np.datetime64('2020-01-01T09:30:00')
    np2 = np.datetime64('2020-01-01T16:00:00')

    interval = Interval(np1, np2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.year == 2020
    assert interval.start.hour == 9
    assert interval.end.hour == 16


def test_interval_with_pandas_nat_raises_assertion():
    """Test that Interval correctly rejects pandas NaT values.

    Mutation: NaT passed through as a date, so Interval raises another
        error or none.
    Oracle: the 'Interval dates cannot be None' assertion message.
    """
    ts1 = pd.Timestamp('2020-01-01 09:30:00')

    with pytest.raises(AssertionError, match='Interval dates cannot be None'):
        Interval(pd.NaT, ts1)

    with pytest.raises(AssertionError, match='Interval dates cannot be None'):
        Interval(ts1, pd.NaT)


def test_interval_with_numpy_nat_raises_assertion():
    """Test that Interval correctly rejects numpy datetime64 NaT values.

    Mutation: NaT passed through as a date, so Interval raises another
        error or none.
    Oracle: the 'Interval dates cannot be None' assertion message.
    """
    np1 = np.datetime64('2020-01-01T09:30:00')

    with pytest.raises(AssertionError, match='Interval dates cannot be None'):
        Interval(np.datetime64('NaT'), np1)

    with pytest.raises(AssertionError, match='Interval dates cannot be None'):
        Interval(np1, np.datetime64('NaT'))


def test_interval_expect_date_or_datetime_mixed_types():
    """Test that Interval normalizes mixed Date and DateTime types to DateTime.

    Mutation: the Date endpoint left as a Date beside a DateTime, or a
        zone other than UTC for naive input.
    Oracle: midnight on the date, and UTC for a naive datetime.
    """
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
    """Test that range operations preserve the converted Date/DateTime types.

    Mutation: range yielding pendulum dates in place of opendate types.
    Oracle: the opendate Date and DateTime classes, 5 days each.
    """
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
    """Test that business operations work with converted types.

    Mutation: business mode lost on endpoints converted from
        datetime.date, so every calendar day counts.
    Oracle: 3 NYSE sessions from 2018-09-06 to 09-10, the end excluded
        from days.
    """
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
    """Test that timezone-aware datetime objects are properly handled.

    Mutation: a timezone-aware datetime converted to UTC.
    Oracle: the EST tzinfo of the inputs.
    """
    dt1 = datetime.datetime(2020, 1, 1, 9, 30, 0, tzinfo=EST)
    dt2 = datetime.datetime(2020, 1, 1, 16, 0, 0, tzinfo=EST)

    interval = Interval(dt1, dt2)

    assert isinstance(interval.start, DateTime)
    assert isinstance(interval.end, DateTime)
    assert interval.start.tzinfo == EST
    assert interval.end.tzinfo == EST


def test_interval_mixed_types_preserves_datetime_timezone():
    """Test that a Date beside a DateTime takes the DateTime's timezone.

    Mutation: the paired Date put in UTC, or the zone read from begdate
        alone, which misses it when the DateTime is enddate.
    Oracle: the EST tzinfo of the DateTime input, in either position.
    """
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


def test_interval_init_decorator_chain():
    """Verify the decorators convert inputs, then pair Date with DateTime.

    Mutation: normalize_date_datetime_pairs run before
        expect_date_or_datetime, so it meets a raw datetime.date and
        leaves it a Date.
    Oracle: the EST tzinfo and hours of the inputs, and the pandas and
        numpy input dates.
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


def test_interval_business_days_across_holiday():
    """Business days count across Good Friday 2024.

    Mutation: Good Friday taken as a business day.
    Oracle: NYSE closed Good Friday 2024-03-29.
    """
    assert Interval(Date(2024, 3, 28), Date(2024, 4, 1)).b.days == 1


def test_interval_business_days_same_day():
    """Same-day interval has 0 business days.

    Mutation: the end day kept in the business count.
    Oracle: an empty span, 2024-04-01 a Monday session.
    """
    assert Interval(Date(2024, 4, 1), Date(2024, 4, 1)).b.days == 0


def test_interval_business_days_weekend_end():
    """Business days when end is weekend (not a business day).

    Mutation: one day subtracted for the end whether or not it is a
        business day.
    Oracle: Friday 2024-04-05 alone, with 04-06 a Saturday.
    """
    assert Interval(Date(2024, 4, 5), Date(2024, 4, 6)).b.days == 1


if __name__ == '__main__':
    __import__('pytest').main([__file__])
