import pytest

from date import NYSE, Date


def test_nyse_business_days():
    """Test NYSE.business_days returns set of business days."""
    begdate = Date(2024, 1, 1)
    enddate = Date(2024, 1, 31)

    business_days = NYSE.business_days(begdate, enddate)
    assert isinstance(business_days, set)
    assert all(isinstance(d, Date) for d in business_days)

    assert Date(2024, 1, 1) not in business_days
    assert Date(2024, 1, 2) in business_days
    assert Date(2024, 1, 6) not in business_days
    assert Date(2024, 1, 7) not in business_days
    assert Date(2024, 1, 8) in business_days


def test_nyse_business_hours():
    """Test NYSE.business_hours returns dict of market hours."""
    begdate = Date(2024, 1, 2)
    enddate = Date(2024, 1, 5)

    hours = NYSE.business_hours(begdate, enddate)
    assert isinstance(hours, dict)

    if Date(2024, 1, 2) in hours:
        open_time, close_time = hours[Date(2024, 1, 2)]
        assert open_time.hour == 9
        assert open_time.minute == 30
        assert close_time.hour == 16
        assert close_time.minute == 0


def test_nyse_business_holidays():
    """Test NYSE.business_holidays returns set of holidays."""
    begdate = Date(2024, 1, 1)
    enddate = Date(2024, 12, 31)

    holidays = NYSE.business_holidays(begdate, enddate)
    assert isinstance(holidays, set)
    assert all(isinstance(d, Date) for d in holidays)

    assert Date(2024, 1, 1) in holidays
    assert Date(2024, 7, 4) in holidays
    assert Date(2024, 12, 25) in holidays

    assert Date(2024, 1, 2) not in holidays


def test_nyse_timezone():
    """Test NYSE has correct timezone."""
    from date import EST
    assert NYSE.tz == EST


def test_nyse_business_days_with_max_date():
    """Test NYSE.business_days handles dates near datetime.MAXYEAR without overflow.
    """
    begdate = Date(9999, 1, 1)
    enddate = Date(9999, 12, 31)

    business_days = NYSE.business_days(begdate, enddate)
    assert isinstance(business_days, set)
    assert all(isinstance(d, Date) for d in business_days)


if __name__ == '__main__':
    pytest.main([__file__])
