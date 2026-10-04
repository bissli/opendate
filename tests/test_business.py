import pytest
from opendate import UTC, Date, DateTime, WeekDay
from opendate.constants import MAX_YEAR, MIN_YEAR


def test_date_business_date_or_next():
    """Verify b.add(days=0) snaps forward off weekends and holidays.

    Mutation: snapping backward on days=0, or counting the start day in
        b.add(days=1).
    Oracle: NYSE calendar; 2018-09-03 is Labor Day.
    """
    # 9/1 is Saturday, 9/3 is Labor Day
    d = Date(2018, 9, 1)\
        .business()\
        .add(days=0)
    assert d == Date(2018, 9, 4)

    # regular Saturday
    d = Date(2024, 3, 30)\
        .business()\
        .add(days=0)
    assert d == Date(2024, 4, 1)

    d = Date(2024, 3, 30)\
        .subtract(days=1)\
        .business()\
        .add(days=1)
    assert d == Date(2024, 4, 1)

    # regular Sunday
    d = Date(2024, 3, 31)\
        .business()\
        .add(days=0)
    assert d == Date(2024, 4, 1)

    d = Date(2024, 3, 31)\
        .subtract(days=1)\
        .business()\
        .add(days=1)
    assert d == Date(2024, 4, 1)

    # regular Monday
    d = Date(2024, 4, 1)\
        .business()\
        .add(days=0)
    assert d == Date(2024, 4, 1)


def test_date_business_date_or_previous():
    """Verify b.subtract(days=0) snaps backward off weekends and holidays.

    Mutation: snapping forward on days=0, or counting the start day in
        b.subtract(days=1).
    Oracle: NYSE calendar; 2024-03-29 is Good Friday.
    """
    # regular Saturday
    d = Date(2024, 3, 30)\
        .business()\
        .subtract(days=0)
    assert d == Date(2024, 3, 28)

    d = Date(2024, 3, 30)\
        .add(days=1)\
        .business()\
        .subtract(days=1)
    assert d == Date(2024, 3, 28)

    # regular Sunday
    d = Date(2024, 3, 31)\
        .business()\
        .subtract(days=0)
    assert d == Date(2024, 3, 28)

    d = Date(2024, 3, 31)\
        .add(days=1)\
        .business()\
        .subtract(days=1)
    assert d == Date(2024, 3, 28)

    # regular Monday
    d = Date(2024, 4, 1)\
        .business()\
        .subtract(days=0)
    assert d == Date(2024, 4, 1)


def test_datetime_is_business_day():
    """Verify is_business_day() and b.add() work on a DateTime.

    Mutation: is_business_day() treating a weekend DateTime as open.
    Oracle: NYSE calendar; 2000-01-01 is a Saturday, 1999-12-31 a Friday.
    """

    d = DateTime(2000, 1, 1, 12, 30)
    assert not d.is_business_day()
    assert d.add(days=2).is_business_day()
    assert d.subtract(days=2).b.add(days=1).is_business_day()


def test_date_first_of():
    """Test first_of method with business mode.

    Mutation: snapping outside business mode, or snapping backward in it.
    Oracle: 2023-07-01 is a Saturday; 2023-04-03 the first Monday of April.
    """
    d = Date(2023, 4, 15).first_of('month')
    assert d == Date(2023, 4, 1)

    # First of month falls on Saturday
    d = Date(2023, 7, 15).first_of('month')
    assert d == Date(2023, 7, 1)

    d = Date(2023, 7, 15).b.first_of('month')
    assert d == Date(2023, 7, 3)

    d = Date(2023, 6, 15).first_of('year')
    assert d == Date(2023, 1, 1)

    d = Date(2023, 4, 15).first_of('month', WeekDay.MONDAY)
    assert d == Date(2023, 4, 3)


def test_date_last_of():
    """Test last_of method with business mode.

    Mutation: snapping outside business mode, or snapping forward in it.
    Oracle: 2023-04-30 is a Sunday; 2023-04-28 the last Friday of April.
    """
    # Last of month falls on Sunday
    d = Date(2023, 4, 15).last_of('month')
    assert d == Date(2023, 4, 30)

    d = Date(2023, 4, 15).b.last_of('month')
    assert d == Date(2023, 4, 28)

    d = Date(2023, 4, 15).last_of('month', WeekDay.FRIDAY)
    assert d == Date(2023, 4, 28)


def test_date_previous():
    """Test previous method with business mode.

    Mutation: business mode snapping self and skipping the weekday move.
    Oracle: 2023-04-10 and 2023-07-03 are Mondays; 2023-06-30 is open.
    """
    d = Date(2023, 4, 10).previous(WeekDay.FRIDAY)
    assert d == Date(2023, 4, 7)

    d = Date(2023, 7, 3).b.previous(WeekDay.FRIDAY)
    assert d == Date(2023, 6, 30)

    d = Date(2023, 4, 10).previous(WeekDay.SUNDAY)
    assert d == Date(2023, 4, 9)


def test_previous_friday_snaps_backward_when_landing_on_july4():
    """Verify b.previous(FRIDAY) snaps backward off a Friday holiday.

    Mutation: previous() snapping forward, as next() does.
    Oracle: NYSE closed Fri 2025-07-04; 2025-07-07 is a Monday.
    """
    d = Date(2025, 7, 7)
    result = d.b.previous(WeekDay.FRIDAY)
    assert result == Date(2025, 7, 3), f'Expected July 3, got {result}'


def test_next_monday_snaps_forward_when_landing_on_memorial_day():
    """Verify b.next(MONDAY) snaps forward off a Monday holiday.

    Mutation: next() snapping backward, as previous() does.
    Oracle: NYSE closed Mon 2024-05-27, Memorial Day; 2024-05-24 is a
        Friday.
    """
    d = Date(2024, 5, 24)
    result = d.b.next(WeekDay.MONDAY)
    assert result == Date(2024, 5, 28), f'Expected May 28, got {result}'


def test_previous_thursday_snaps_backward_when_landing_on_thanksgiving():
    """Verify b.previous(THURSDAY) snaps backward off Thanksgiving.

    Mutation: previous() snapping forward, as next() does.
    Oracle: NYSE closed Thu 2024-11-28, Thanksgiving; 2024-12-02 is a
        Monday.
    """
    d = Date(2024, 12, 2)
    result = d.b.previous(WeekDay.THURSDAY)
    assert result == Date(2024, 11, 27), f'Expected Nov 27, got {result}'


def test_negative_add_business():
    """Test b.add(days=-N) from weekday, crossing holidays.

    Mutation: a negative count stepping calendar days, or skipping no
        holidays.
    Oracle: NYSE closures noted inline.
    """
    # 2024-03-29 is Good Friday (closed)
    assert Date(2024, 4, 1).b.add(days=-1) == Date(2024, 3, 28)
    assert Date(2024, 4, 1).b.add(days=-2) == Date(2024, 3, 27)
    assert Date(2024, 4, 1).b.add(days=-3) == Date(2024, 3, 26)

    # 2018-12-05 closed for Bush funeral
    assert Date(2018, 12, 6).b.add(days=-2) == Date(2018, 12, 3)


def test_negative_subtract_business():
    """Test b.subtract(days=-N) from weekday goes forward.

    Mutation: subtract() dropping the sign and moving backward.
    Oracle: hand-counted NYSE days from Mon 2024-04-01.
    """
    assert Date(2024, 4, 1).b.subtract(days=-1) == Date(2024, 4, 2)
    assert Date(2024, 4, 1).b.subtract(days=-3) == Date(2024, 4, 4)
    assert Date(2024, 4, 1).b.subtract(days=-5) == Date(2024, 4, 8)


def test_negative_days_from_non_business_day():
    """Test negative days starting from weekend or holiday.

    Mutation: counting the non-business start day as the first step.
    Oracle: NYSE closures noted inline.
    """
    # Saturday 3/30, Good Friday 3/29 closed
    assert Date(2024, 3, 30).b.add(days=-1) == Date(2024, 3, 28)
    assert Date(2024, 3, 31).b.add(days=-1) == Date(2024, 3, 28)
    assert Date(2024, 3, 30).b.add(days=-3) == Date(2024, 3, 26)

    # subtract(days=-N) from Sunday goes forward
    assert Date(2024, 3, 31).b.subtract(days=-1) == Date(2024, 4, 1)

    # from Good Friday itself
    assert Date(2024, 3, 29).b.add(days=-1) == Date(2024, 3, 28)
    assert Date(2024, 3, 29).b.add(days=-3) == Date(2024, 3, 26)


@pytest.mark.parametrize(
    ('start', 'n'),
    [
        (Date(2024, 4, 10), 1),
        (Date(2024, 4, 10), 3),
        (Date(2024, 4, 10), 5),
        (Date(2024, 4, 10), 10),
        (Date(2024, 4, 1), 1),
        (Date(2024, 4, 1), 5),
        (Date(2018, 12, 7), 5),
        (Date(2021, 11, 24), 5),
        (Date(2020, 1, 2), 1),
        (Date(2020, 1, 2), 3),
        (Date(2020, 1, 3), 5),
        (Date(2010, 1, 4), 3),
        ])
def test_negative_days_equivalence(start, n):
    """Test b.add(days=-N) == b.subtract(days=N) and vice versa.

    Mutation: the days < 0 branch of add() or subtract() keeping the sign,
        or losing business mode on the handoff.
    Oracle: the opposite method with a positive count; the 2010 and 2020
        starts cross a decade boundary.
    """
    assert start.b.add(days=-n) == start.b.subtract(days=n)
    assert start.b.subtract(days=-n) == start.b.add(days=n)


def test_negative_days_custom_calendar():
    """Test negative days with LSE vs NYSE (Easter Monday divergence).

    Mutation: the negative-days handoff dropping the calendar for NYSE.
    Oracle: Easter Monday 2024-04-01 is closed on LSE, open on NYSE.
    """
    assert Date(2024, 4, 2).calendar('LSE').b.add(days=-1) == Date(2024, 3, 28)
    assert Date(2024, 4, 2).calendar('NYSE').b.add(days=-1) == Date(2024, 4, 1)
    assert Date(2024, 4, 2).calendar('LSE').b.add(days=-2) == Date(2024, 3, 27)
    assert Date(2024, 4, 2).calendar('NYSE').b.add(days=-2) == Date(2024, 3, 28)


def test_subtract_from_holiday_on_decade_boundary():
    """Subtract 1 business day from New Year's Day at decade boundaries.

    Mutation: decade bounds without the padding year, so the step off
        Jan 1 finds no earlier business day.
    Oracle: NYSE closes on Jan 1; Dec 31 of each prior year is open.
    """
    assert Date(2020, 1, 1).b.subtract(days=1) == Date(2019, 12, 31)
    assert Date(2010, 1, 1).b.subtract(days=1) == Date(2009, 12, 31)
    assert Date(2000, 1, 1).b.subtract(days=1) == Date(1999, 12, 31)


def test_subtract_from_business_day_near_decade_boundary():
    """Subtract business days from first business days of a decade.

    Mutation: decade bounds without the leading padding year.
    Oracle: hand-counted NYSE days; 2020-01-01 is closed.
    """
    assert Date(2020, 1, 2).b.subtract(days=1) == Date(2019, 12, 31)
    assert Date(2020, 1, 2).b.subtract(days=2) == Date(2019, 12, 30)
    assert Date(2020, 1, 3).b.subtract(days=3) == Date(2019, 12, 30)


def test_add_forward_across_decade_boundary():
    """Add business days forward from last business day of a decade.

    Mutation: decade bounds without the trailing padding year.
    Oracle: hand-counted NYSE days; Jan 1 is closed, 2010-01-02/03 a
        weekend.
    """
    assert Date(2029, 12, 31).b.add(days=1) == Date(2030, 1, 2)
    assert Date(2019, 12, 31).b.add(days=1) == Date(2020, 1, 2)
    assert Date(2009, 12, 31).b.add(days=1) == Date(2010, 1, 4)


def test_multiday_spanning_decade_boundary():
    """Multi-day business day operations that span a decade boundary.

    Mutation: decade bounds without padding on either side.
    Oracle: hand-counted NYSE days across 2019-12-27..2020-01-06.
    """
    assert Date(2020, 1, 6).b.subtract(days=5) == Date(2019, 12, 27)
    assert Date(2019, 12, 27).b.add(days=5) == Date(2020, 1, 6)


def test_snap_backward_at_decade_boundary():
    """subtract(days=0) snaps back to a business day across a decade boundary.

    Mutation: _snap_to_business_day using a calendar without the
        leading padding year.
    Oracle: NYSE closes on Jan 1; Dec 31 of each prior year is open.
    """
    assert Date(2020, 1, 1).b.subtract(days=0) == Date(2019, 12, 31)
    assert Date(2010, 1, 1).b.subtract(days=0) == Date(2009, 12, 31)


def test_custom_calendar_at_decade_boundary():
    """LSE calendar subtract across decade boundary.

    Mutation: the LSE decade calendar built without padding.
    Oracle: LSE closes on Jan 1; 2019-12-31 is open.
    """
    assert (
        Date(2020, 1, 2).calendar('LSE').b.subtract(days=1)
        == Date(2019, 12, 31)
        )


@pytest.mark.parametrize('boundary_year', [MAX_YEAR, MIN_YEAR + 10])
def test_subtract_across_decade_boundary_at_range_edge(boundary_year):
    """Business day subtract across a decade boundary at the range edges.

    Mutation: decade bounds without the leading padding year, so the first
        business day of the MAX_YEAR decade, or of the second decade after
        MIN_YEAR, cannot reach the prior year.
    Oracle: is_business_day walks out from each side of the boundary.
    """
    first_bd = Date(boundary_year, 1, 1)
    while not first_bd.is_business_day():
        first_bd = first_bd.add(days=1)
    prev_bd = Date(boundary_year - 1, 12, 31)
    while not prev_bd.is_business_day():
        prev_bd = prev_bd.subtract(days=1)
    assert first_bd.b.subtract(days=1) == prev_bd


def test_business_add_preserves_sub_day_kwargs():
    """b.add(days=1, hours=2) should apply both business days and hours.

    Mutation: kwargs dropped after the business-day move.
    Oracle: hand-computed Mon 09:00 plus one business day and 2h.
    """
    dt = DateTime(2024, 4, 1, 9, 0, 0, tzinfo=UTC)
    result = dt.b.add(days=1, hours=2)
    assert result == DateTime(2024, 4, 2, 11, 0, 0, tzinfo=UTC)


def test_business_subtract_preserves_sub_day_kwargs():
    """b.subtract(days=1, hours=2) should apply both business days and hours.

    Mutation: kwargs dropped, or added, after the business-day move.
    Oracle: hand-computed Tue 14:00 less one business day and 2h.
    """
    dt = DateTime(2024, 4, 2, 14, 0, 0, tzinfo=UTC)
    result = dt.b.subtract(days=1, hours=2)
    assert result == DateTime(2024, 4, 1, 12, 0, 0, tzinfo=UTC)


def test_is_business_day_preserves_calendar_on_datetime():
    """Verify DateTime.is_business_day() uses the DateTime's own calendar.

    Mutation: the Date copy in is_business_day() dropping _calendar.
    Oracle: Easter Monday 2024-04-01 is closed on LSE, open on NYSE.
    """
    dt = DateTime(2024, 4, 1, 12, 0, 0, tzinfo=UTC)
    assert dt.calendar('LSE').is_business_day() is False
    assert dt.calendar('NYSE').is_business_day() is True


def test_business_hours_preserves_calendar_on_datetime():
    """Verify DateTime.business_hours() uses the DateTime's own calendar.

    Mutation: the Date copy in business_hours() dropping _calendar.
    Oracle: NYSE and LSE sessions open at different UTC times.
    """
    dt = DateTime(2024, 4, 2, 12, 0, 0, tzinfo=UTC)
    nyse_hours = dt.calendar('NYSE').business_hours()
    lse_hours = dt.calendar('LSE').business_hours()
    assert nyse_hours != lse_hours


def test_is_business_day_uses_wallclock_date():
    """is_business_day uses the DateTime's wall-clock date.

    Mutation: converting to the calendar's tz before taking the date.
    Oracle: 2024-04-06 is a Saturday; 02:00 UTC is still Friday in New York.
    """
    dt = DateTime(2024, 4, 6, 2, 0, 0, tzinfo=UTC)
    assert dt.is_business_day() is False


if __name__ == '__main__':
    __import__('pytest').main([__file__])
