from date import Date, DateTime, WeekDay


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


if __name__ == '__main__':
    __import__('pytest').main([__file__])
