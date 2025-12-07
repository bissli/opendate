import pytest

from date import CustomCalendar, Date, ExchangeCalendar
from date import available_calendars, get_calendar, register_calendar


def test_available_calendars():
    """Test available_calendars returns list of exchange names."""
    cals = available_calendars()
    assert isinstance(cals, list)
    assert 'NYSE' in cals
    assert 'LSE' in cals
    assert 'NASDAQ' in cals
    assert len(cals) > 100


def test_get_calendar_nyse():
    """Test get_calendar returns NYSE calendar."""
    nyse = get_calendar('NYSE')
    assert isinstance(nyse, ExchangeCalendar)
    assert nyse.name == 'NYSE'


def test_get_calendar_caching():
    """Test that get_calendar returns cached instances."""
    nyse1 = get_calendar('NYSE')
    nyse2 = get_calendar('NYSE')
    assert nyse1 is nyse2


def test_get_calendar_invalid():
    """Test get_calendar raises on invalid name."""
    with pytest.raises(ValueError, match='Unknown calendar'):
        get_calendar('INVALID_EXCHANGE')


def test_nyse_business_days():
    """Test NYSE calendar returns set of business days."""
    nyse = get_calendar('NYSE')
    begdate = Date(2024, 1, 1)
    enddate = Date(2024, 1, 31)

    business_days = nyse.business_days(begdate, enddate)
    assert isinstance(business_days, set)
    assert all(isinstance(d, Date) for d in business_days)

    assert Date(2024, 1, 1) not in business_days
    assert Date(2024, 1, 2) in business_days
    assert Date(2024, 1, 6) not in business_days
    assert Date(2024, 1, 7) not in business_days
    assert Date(2024, 1, 8) in business_days


def test_nyse_business_hours():
    """Test NYSE calendar returns dict of market hours."""
    nyse = get_calendar('NYSE')
    begdate = Date(2024, 1, 2)
    enddate = Date(2024, 1, 5)

    hours = nyse.business_hours(begdate, enddate)
    assert isinstance(hours, dict)

    if Date(2024, 1, 2) in hours:
        open_time, close_time = hours[Date(2024, 1, 2)]
        assert open_time.hour == 9
        assert open_time.minute == 30
        assert close_time.hour == 16
        assert close_time.minute == 0


def test_nyse_business_holidays():
    """Test NYSE calendar returns set of holidays."""
    nyse = get_calendar('NYSE')
    begdate = Date(2024, 1, 1)
    enddate = Date(2024, 12, 31)

    holidays = nyse.business_holidays(begdate, enddate)
    assert isinstance(holidays, set)
    assert all(isinstance(d, Date) for d in holidays)

    assert Date(2024, 1, 1) in holidays
    assert Date(2024, 7, 4) in holidays
    assert Date(2024, 12, 25) in holidays

    assert Date(2024, 1, 2) not in holidays


def test_nyse_timezone():
    """Test NYSE calendar has correct timezone."""
    nyse = get_calendar('NYSE')
    # NYSE uses America/New_York (which is equivalent to US/Eastern)
    assert 'America/New_York' in str(nyse.tz) or 'US/Eastern' in str(nyse.tz)


def test_nyse_business_days_with_max_date():
    """Test NYSE calendar handles dates near datetime.MAXYEAR without overflow."""
    nyse = get_calendar('NYSE')
    begdate = Date(9999, 1, 1)
    enddate = Date(9999, 12, 31)

    business_days = nyse.business_days(begdate, enddate)
    assert isinstance(business_days, set)
    assert all(isinstance(d, Date) for d in business_days)


def test_lse_calendar():
    """Test LSE calendar works correctly."""
    lse = get_calendar('LSE')
    assert isinstance(lse, ExchangeCalendar)
    assert lse.name == 'LSE'
    assert 'Europe/London' in str(lse.tz)


def test_custom_calendar_basic():
    """Test CustomCalendar with basic configuration."""
    # Custom calendar with Boxing Day, Dec 27, and Christmas as company holidays
    holidays = {Date(2024, 12, 25), Date(2024, 12, 26), Date(2024, 12, 27)}
    cal = CustomCalendar(name='MyCompany', holidays=holidays)

    assert cal.name == 'MyCompany'

    begdate = Date(2024, 12, 23)
    enddate = Date(2024, 12, 31)
    bdays = cal.business_days(begdate, enddate)

    # Custom holidays
    assert Date(2024, 12, 25) not in bdays
    assert Date(2024, 12, 26) not in bdays
    assert Date(2024, 12, 27) not in bdays
    # Regular business days
    assert Date(2024, 12, 23) in bdays
    assert Date(2024, 12, 24) in bdays
    assert Date(2024, 12, 30) in bdays
    # Weekends still excluded
    assert Date(2024, 12, 28) not in bdays  # Saturday
    assert Date(2024, 12, 29) not in bdays  # Sunday


def test_custom_calendar_with_callable_holidays():
    """Test CustomCalendar with holidays as callable."""
    def get_holidays(begdate, enddate):
        return {Date(2024, 7, 5)}

    cal = CustomCalendar(holidays=get_holidays)
    bdays = cal.business_days(Date(2024, 7, 1), Date(2024, 7, 10))

    assert Date(2024, 7, 4) in bdays
    assert Date(2024, 7, 5) not in bdays


def test_register_calendar():
    """Test register_calendar adds custom calendar to registry."""
    cal = CustomCalendar(name='TestCal', holidays={Date(2024, 1, 2)})
    register_calendar('TESTCAL', cal)

    retrieved = get_calendar('TESTCAL')
    assert retrieved is cal


def test_date_with_calendar_method():
    """Test Date.calendar() method works correctly."""
    d = Date(2024, 1, 1).calendar('NYSE')
    assert d._calendar is not None
    assert isinstance(d._calendar, ExchangeCalendar)


def test_date_business_with_string_calendar():
    """Test Date business operations with string calendar."""
    d = Date(2024, 1, 1).calendar('NYSE').b.add(days=1)
    assert d == Date(2024, 1, 2)


if __name__ == '__main__':
    pytest.main([__file__])
