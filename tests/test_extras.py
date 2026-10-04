import inspect
from unittest.mock import patch

import opendate
import pytest
from opendate import EST, Date, DateTime, get_calendar
from opendate.extras import create_ics, is_business_day
from opendate.extras import is_within_business_hours, overlap_days


def test_is_within_business_hours():
    """Test is_within_business_hours with various scenarios.

    Mutation: dropping the business_open() test, or the hours bounds.
    Oracle: NYSE 09:30-16:00 hours on Monday 2000-05-01 at 12:30,
        Sunday 2000-07-02 at 12:15 and Wednesday 2000-11-01 at 01:15.
    """
    tz = get_calendar('NYSE').tz

    with patch('opendate.DateTime.now') as mock:
        mock.return_value = DateTime(2000, 5, 1, 12, 30, 0, 0, tzinfo=tz)
        assert is_within_business_hours() is True

    with patch('opendate.DateTime.now') as mock:
        mock.return_value = DateTime(2000, 7, 2, 12, 15, 0, 0, tzinfo=tz)
        assert is_within_business_hours() is False

    with patch('opendate.DateTime.now') as mock:
        mock.return_value = DateTime(2000, 11, 1, 1, 15, 0, 0, tzinfo=tz)
        assert is_within_business_hours() is False


def test_overlap_days_boolean():
    """Test overlap_days with boolean return (days=False).

    Mutation: min and max swapped in latest_start and earliest_end.
    Oracle: hand-picked March 2016 ranges, disjoint, crossed and nested.
    """
    date1 = Date(2016, 3, 1)
    date2 = Date(2016, 3, 2)
    date3 = Date(2016, 3, 29)
    date4 = Date(2016, 3, 30)

    assert overlap_days((date1, date3), (date2, date4)) is True
    assert overlap_days((date2, date4), (date1, date3)) is True
    assert overlap_days((date1, date2), (date3, date4)) is False

    assert overlap_days((date1, date4), (date1, date4)) is True
    assert overlap_days((date1, date4), (date2, date3)) is True


def test_overlap_days_count():
    """Test overlap_days with day count return (days=True).

    Mutation: dropping the + 1 that counts both endpoints.
    Oracle: hand-counted days, 30 for March 1-30 inclusive.
    """
    date1 = Date(2016, 3, 1)
    date2 = Date(2016, 3, 2)
    date3 = Date(2016, 3, 29)
    date4 = Date(2016, 3, 30)

    assert overlap_days((date1, date4), (date1, date4), True) == 30
    assert overlap_days((date2, date3), (date1, date4), True) == 28
    assert overlap_days((date3, date4), (date1, date2), True) == -26


def test_is_business_day():
    """Test is_business_day with various scenarios.

    Mutation: ignoring the NYSE holiday list, or the weekend test.
    Oracle: Monday 2018-11-19, the weekend 2018-11-24/25, and Monday
        2021-07-05, the NYSE Independence Day holiday.
    """
    tz = get_calendar('NYSE').tz

    with patch('opendate.DateTime.now') as mock:
        mock.return_value = DateTime(2018, 11, 19, 12, 30, 0, 0, tzinfo=tz)
        assert is_business_day() is True

    with patch('opendate.DateTime.now') as mock:
        mock.return_value = DateTime(2018, 11, 24, 12, 30, 0, 0, tzinfo=tz)
        assert is_business_day() is False

    with patch('opendate.DateTime.now') as mock:
        mock.return_value = DateTime(2018, 11, 25, 12, 30, 0, 0, tzinfo=tz)
        assert is_business_day() is False

    with patch('opendate.DateTime.now') as mock:
        mock.return_value = DateTime(2021, 7, 5, 12, 30, 0, 0, tzinfo=tz)
        assert is_business_day() is False


def test_create_ics_with_datetime():
    """Test create_ics with DateTime objects generates valid iCalendar format.

    Mutation: begdate and enddate swapped, or seconds dropped from the
        DTSTART/DTEND format.
    Oracle: hand-written RFC 5545 lines for 09:30-16:00 on 2024-01-15.
    """
    begdate = DateTime(2024, 1, 15, 9, 30, 0, tzinfo=EST)
    enddate = DateTime(2024, 1, 15, 16, 0, 0, tzinfo=EST)
    summary = 'Test Meeting'
    location = 'Conference Room A'

    ics_content = create_ics(begdate, enddate, summary, location)

    assert 'BEGIN:VCALENDAR' in ics_content
    assert 'VERSION:2.0' in ics_content
    assert 'BEGIN:VEVENT' in ics_content
    assert 'END:VEVENT' in ics_content
    assert 'END:VCALENDAR' in ics_content
    assert 'DTSTART;TZID=America/New_York:20240115T093000' in ics_content
    assert 'DTEND;TZID=America/New_York:20240115T160000' in ics_content
    assert 'SUMMARY:Test Meeting' in ics_content
    assert 'LOCATION:Conference Room A' in ics_content


def test_create_ics_with_date():
    """Test create_ics with Date objects generates valid iCalendar format.

    Mutation: a Date written without its T000000 time part.
    Oracle: hand-written RFC 5545 midnight lines for 2024-01-15.
    """

    begdate = Date(2024, 1, 15)
    enddate = Date(2024, 1, 15)
    summary = 'All Day Event'
    location = 'Virtual'

    ics_content = create_ics(begdate, enddate, summary, location)

    assert 'BEGIN:VCALENDAR' in ics_content
    assert 'VERSION:2.0' in ics_content
    assert 'BEGIN:VEVENT' in ics_content
    assert 'END:VEVENT' in ics_content
    assert 'END:VCALENDAR' in ics_content
    assert 'DTSTART;TZID=America/New_York:20240115T000000' in ics_content
    assert 'DTEND;TZID=America/New_York:20240115T000000' in ics_content
    assert 'SUMMARY:All Day Event' in ics_content
    assert 'LOCATION:Virtual' in ics_content


def test_is_within_business_hours_has_no_datetime_param():
    """is_within_business_hours takes calendar as its only parameter.

    Mutation: a datetime parameter added back to is_within_business_hours.
    Oracle: the parameter list ['calendar'].
    """
    sig = inspect.signature(is_within_business_hours)
    assert list(sig.parameters.keys()) == ['calendar']


def test_next_relative_date_of_week_by_day():
    """Verify the weekday code picks this date or the next date on it.

    Mutation: WEEKDAY_SHORTNAME.get(day) in place of WEEKDAY_SHORTNAME[day],
        so an unknown code moves one week instead of raising.
    Oracle: Wednesday 2024-01-10 and the January 2024 calendar. dateutil's
        weekday codes MO..SU are upper case.
    """
    wednesday = Date(2024, 1, 10)
    assert wednesday.next_relative_date_of_week_by_day('WE') == wednesday
    assert wednesday.next_relative_date_of_week_by_day('MO') == Date(2024, 1, 15)
    assert wednesday.next_relative_date_of_week_by_day('SU') == Date(2024, 1, 14)
    for code in ('XX', 'mo'):
        with pytest.raises(KeyError):
            wednesday.next_relative_date_of_week_by_day(code)


@pytest.mark.parametrize('func', [opendate.datetime, opendate.time])
def test_tzinfo_annotation_admits_no_float(func):
    """The tzinfo annotation of datetime() and time() leaves out float.

    Mutation: float added back to the tzinfo annotation.
    Oracle: the docstring's 'str, tzinfo or None', and the TypeError
        DateTime and Time raise on a float tzinfo.
    """
    annotation = inspect.signature(func).parameters['tzinfo'].annotation
    assert 'float' not in annotation


if __name__ == '__main__':
    pytest.main([__file__])
