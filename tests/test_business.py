from opendate import Date, DateTime, WeekDay


def test_date_business_date_or_next():
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

    # 3/29 is Good Friday

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
    """Testing that `business day` function (designed for Date)
    works for DateTime object
    """

    d = DateTime(2000, 1, 1, 12, 30)
    assert not d.is_business_day()
    assert d.add(days=2).is_business_day()
    assert d.subtract(days=2).b.add(days=1).is_business_day()


def test_date_first_of():
    """Test first_of method with business mode."""
    # Regular first of month
    d = Date(2023, 4, 15).first_of('month')
    assert d == Date(2023, 4, 1)

    # First of month falls on Saturday
    d = Date(2023, 7, 15).first_of('month')
    assert d == Date(2023, 7, 1)

    # First of month with business mode (Saturday -> Monday)
    d = Date(2023, 7, 15).b.first_of('month')
    assert d == Date(2023, 7, 3)

    # First of year
    d = Date(2023, 6, 15).first_of('year')
    assert d == Date(2023, 1, 1)

    # First Monday of month
    d = Date(2023, 4, 15).first_of('month', WeekDay.MONDAY)
    assert d == Date(2023, 4, 3)


def test_date_last_of():
    """Test last_of method with business mode."""
    # Regular last of month
    d = Date(2023, 4, 15).last_of('month')
    assert d == Date(2023, 4, 30)

    # Last of month falls on Sunday
    d = Date(2023, 4, 15).last_of('month')
    assert d == Date(2023, 4, 30)

    # Last of month with business mode (Sunday -> Friday)
    d = Date(2023, 4, 15).b.last_of('month')
    assert d == Date(2023, 4, 28)

    # Last Friday of month
    d = Date(2023, 4, 15).last_of('month', WeekDay.FRIDAY)
    assert d == Date(2023, 4, 28)


def test_date_previous():
    """Test previous method with business mode."""
    # Regular previous Friday
    d = Date(2023, 4, 10).previous(WeekDay.FRIDAY)  # Monday
    assert d == Date(2023, 4, 7)

    # Previous with business mode should find previous business day occurrence
    d = Date(2023, 7, 3).b.previous(WeekDay.FRIDAY)  # Monday before July 4th holiday
    assert d == Date(2023, 6, 30)

    # Previous Sunday (weekend)
    d = Date(2023, 4, 10).previous(WeekDay.SUNDAY)
    assert d == Date(2023, 4, 9)


def test_previous_friday_snaps_backward_when_landing_on_july4():
    """previous(FRIDAY) in business mode should snap backward when landing on holiday.

    July 4, 2025 is Friday (Independence Day - holiday)
    July 7, 2025 is Monday

    d.b.previous(FRIDAY) from Monday finds previous Friday = July 4 (holiday).
    Should snap BACKWARD to July 3 (Thursday).
    """
    d = Date(2025, 7, 7)  # Monday
    result = d.b.previous(WeekDay.FRIDAY)  # Previous Friday = July 4 (holiday)

    # Should be July 3 (Thursday) - snap backward from holiday
    assert result == Date(2025, 7, 3), f'Expected July 3, got {result}'


def test_next_monday_snaps_forward_when_landing_on_memorial_day():
    """next(MONDAY) in business mode should snap forward when landing on holiday.

    Memorial Day 2024: May 27 is Monday (holiday)
    May 24, 2024 is Friday

    d.b.next(MONDAY) from Friday finds next Monday = May 27 (holiday).
    Should snap FORWARD to May 28 (Tuesday).
    """
    d = Date(2024, 5, 24)  # Friday
    result = d.b.next(WeekDay.MONDAY)  # Next Monday = May 27 (Memorial Day)

    # Should be May 28 (Tuesday) - snap forward from holiday
    assert result == Date(2024, 5, 28), f'Expected May 28, got {result}'


def test_previous_thursday_snaps_backward_when_landing_on_thanksgiving():
    """previous(THURSDAY) in business mode should snap backward for Thanksgiving.

    Thanksgiving 2024: November 28 is Thursday (holiday)
    December 2, 2024 is Monday

    d.b.previous(THURSDAY) from Monday finds previous Thursday = Nov 28 (holiday).
    Should snap BACKWARD to November 27 (Wednesday).
    """
    d = Date(2024, 12, 2)  # Monday
    result = d.b.previous(WeekDay.THURSDAY)  # Previous Thursday = Nov 28 (Thanksgiving)

    # Should be Nov 27 (Wednesday) - snap backward from holiday
    assert result == Date(2024, 11, 27), f'Expected Nov 27, got {result}'


if __name__ == '__main__':
    __import__('pytest').main([__file__])
