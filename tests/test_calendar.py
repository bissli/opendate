import pytest

from opendate import CustomCalendar, Date, ExchangeCalendar
from opendate import available_calendars, get_calendar, register_calendar


def test_available_calendars():
    """Test available_calendars returns list of exchange names.

    Mutation: listing the registered calendars in place of the exchanges.
    Oracle: NYSE, LSE and NASDAQ, which pandas_market_calendars ships.
    """
    cals = available_calendars()
    assert isinstance(cals, list)
    assert 'NYSE' in cals
    assert 'LSE' in cals
    assert 'NASDAQ' in cals
    assert len(cals) > 100


def test_get_calendar_nyse():
    """Test get_calendar returns NYSE calendar.

    Mutation: get_calendar returning a CustomCalendar, or keeping the
        caller's case in name.
    Oracle: the exchange name 'NYSE'.
    """
    nyse = get_calendar('NYSE')
    assert isinstance(nyse, ExchangeCalendar)
    assert nyse.name == 'NYSE'


def test_get_calendar_caching():
    """Test that get_calendar returns cached instances.

    Mutation: get_calendar building a new ExchangeCalendar per call.
    Oracle: object identity across two calls.
    """
    nyse1 = get_calendar('NYSE')
    nyse2 = get_calendar('NYSE')
    assert nyse1 is nyse2


def test_get_calendar_invalid():
    """Test get_calendar raises on invalid name.

    Mutation: an unknown name falling through to ExchangeCalendar, which
        raises RuntimeError.
    Oracle: the documented ValueError message.
    """
    with pytest.raises(ValueError, match='Unknown calendar'):
        get_calendar('INVALID_EXCHANGE')


def test_nyse_business_days():
    """Test NYSE calendar returns set of business days.

    Mutation: business_days keeping holidays or weekends.
    Oracle: 2024-01-01 is New Year's Day; 2024-01-06/07 a weekend.
    """
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
    """Test NYSE calendar returns dict of market hours.

    Mutation: the schedule read in UTC.
    Oracle: NYSE trades 09:30 to 16:00 New York time.
    """
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
    """Test NYSE calendar returns set of holidays.

    Mutation: the begdate..enddate filter made exclusive at either end.
    Oracle: NYSE closes 2024-01-01, 2024-07-04 and 2024-12-25.
    """
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
    """Test NYSE calendar has correct timezone.

    Mutation: tz left at the Calendar default, UTC.
    Oracle: NYSE trades on New York time.
    """
    nyse = get_calendar('NYSE')
    assert 'America/New_York' in str(nyse.tz) or 'US/Eastern' in str(nyse.tz)


def test_nyse_business_days_with_max_date():
    """Test NYSE calendar handles dates near MAXYEAR without overflow.

    Mutation: dropping the None check on the decade bounds, which raises.
    Oracle: no exception, and a set of Date.
    """
    nyse = get_calendar('NYSE')
    begdate = Date(9999, 1, 1)
    enddate = Date(9999, 12, 31)

    business_days = nyse.business_days(begdate, enddate)
    assert isinstance(business_days, set)
    assert all(isinstance(d, Date) for d in business_days)


def test_lse_calendar():
    """Test LSE calendar works correctly.

    Mutation: get_calendar ignoring name and returning NYSE.
    Oracle: LSE trades on London time.
    """
    lse = get_calendar('LSE')
    assert isinstance(lse, ExchangeCalendar)
    assert lse.name == 'LSE'
    assert 'Europe/London' in str(lse.tz)


def test_custom_calendar_basic():
    """Test CustomCalendar with basic configuration.

    Mutation: business_days ignoring holidays or the weekmask.
    Oracle: hand-read December 2024; the 28th and 29th are a weekend.
    """
    holidays = {Date(2024, 12, 25), Date(2024, 12, 26), Date(2024, 12, 27)}
    cal = CustomCalendar(name='MyCompany', holidays=holidays)

    assert cal.name == 'MyCompany'

    begdate = Date(2024, 12, 23)
    enddate = Date(2024, 12, 31)
    bdays = cal.business_days(begdate, enddate)

    assert Date(2024, 12, 25) not in bdays
    assert Date(2024, 12, 26) not in bdays
    assert Date(2024, 12, 27) not in bdays
    assert Date(2024, 12, 23) in bdays
    assert Date(2024, 12, 24) in bdays
    assert Date(2024, 12, 30) in bdays
    assert Date(2024, 12, 28) not in bdays
    assert Date(2024, 12, 29) not in bdays


def test_custom_calendar_with_callable_holidays():
    """Test CustomCalendar with holidays as callable.

    Mutation: a callable holidays source treated as an empty set.
    Oracle: the callable's one holiday, 2024-07-05.
    """
    def get_holidays(begdate, enddate):
        return {Date(2024, 7, 5)}

    cal = CustomCalendar(holidays=get_holidays)
    bdays = cal.business_days(Date(2024, 7, 1), Date(2024, 7, 10))

    assert Date(2024, 7, 4) in bdays
    assert Date(2024, 7, 5) not in bdays


def test_register_calendar():
    """Test register_calendar adds custom calendar to registry.

    Mutation: register_calendar storing a key get_calendar never reads.
    Oracle: object identity with the registered instance.
    """
    cal = CustomCalendar(name='TestCal', holidays={Date(2024, 1, 2)})
    register_calendar('TESTCAL', cal)

    retrieved = get_calendar('TESTCAL')
    assert retrieved is cal


def test_date_with_calendar_method():
    """Test Date.calendar() method works correctly.

    Mutation: calendar() storing the name string in _calendar.
    Oracle: get_calendar('NYSE') returns an ExchangeCalendar.
    """
    d = Date(2024, 1, 1).calendar('NYSE')
    assert d._calendar is not None
    assert isinstance(d._calendar, ExchangeCalendar)


def test_date_business_with_string_calendar():
    """Test Date business operations with string calendar.

    Mutation: b.add(days=1) from a holiday counting the holiday itself.
    Oracle: NYSE closes 2024-01-01; 2024-01-02 is open.
    """
    d = Date(2024, 1, 1).calendar('NYSE').b.add(days=1)
    assert d == Date(2024, 1, 2)


if __name__ == '__main__':
    pytest.main([__file__])
