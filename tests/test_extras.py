from unittest.mock import patch

import pytest

from date import EST, NYSE, Date, DateTime, Interval
from date.extras import end_of_range, is_business_day, is_within_business_hours, overlap_days, start_of_range


def test_is_within_business_hours():
    """Test is_within_business_hours with various scenarios.
    """
    tz = NYSE.tz

    with patch('date.DateTime.now') as mock:
        mock.return_value = DateTime(2000, 5, 1, 12, 30, 0, 0, tzinfo=tz)
        assert is_within_business_hours() is True

    with patch('date.DateTime.now') as mock:
        mock.return_value = DateTime(2000, 7, 2, 12, 15, 0, 0, tzinfo=tz)
        assert is_within_business_hours() is False

    with patch('date.DateTime.now') as mock:
        mock.return_value = DateTime(2000, 11, 1, 1, 15, 0, 0, tzinfo=tz)
        assert is_within_business_hours() is False


def test_overlap_days_boolean():
    """Test overlap_days with boolean return (days=False).
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
    """
    tz = NYSE.tz

    with patch('date.DateTime.now') as mock:
        mock.return_value = DateTime(2018, 11, 19, 12, 30, 0, 0, tzinfo=tz)
        assert is_business_day() is True

    with patch('date.DateTime.now') as mock:
        mock.return_value = DateTime(2018, 11, 24, 12, 30, 0, 0, tzinfo=tz)
        assert is_business_day() is False

    with patch('date.DateTime.now') as mock:
        mock.return_value = DateTime(2018, 11, 25, 12, 30, 0, 0, tzinfo=tz)
        assert is_business_day() is False

    with patch('date.DateTime.now') as mock:
        mock.return_value = DateTime(2021, 7, 5, 12, 30, 0, 0, tzinfo=tz)
        assert is_business_day() is False


def test_start_of_range_months():
    """Test start_of_range with month unit.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = start_of_range(interval, 'month')
    assert result == [Date(2018, 1, 1), Date(2018, 2, 1), Date(2018, 3, 1), Date(2018, 4, 1)]

    interval = Interval(Date(2018, 4, 30), Date(2018, 7, 30))
    result = start_of_range(interval, 'month')
    assert result == [Date(2018, 4, 1), Date(2018, 5, 1), Date(2018, 6, 1), Date(2018, 7, 1)]


def test_start_of_range_weeks():
    """Test start_of_range with week unit.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = start_of_range(interval, 'week')
    assert result == [Date(2018, 1, 1), Date(2018, 1, 8), Date(2018, 1, 15), Date(2018, 1, 22)]


def test_start_of_range_single_month():
    """Test start_of_range with interval within a single month.
    """
    interval = Interval(Date(2018, 3, 15), Date(2018, 3, 25))
    result = start_of_range(interval, 'month')
    assert result == [Date(2018, 3, 1)]


def test_end_of_range_months():
    """Test end_of_range with month unit.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 4, 5))
    result = end_of_range(interval, 'month')
    assert result == [Date(2018, 1, 31), Date(2018, 2, 28), Date(2018, 3, 31), Date(2018, 4, 30)]

    interval = Interval(Date(2018, 4, 30), Date(2018, 7, 30))
    result = end_of_range(interval, 'month')
    assert result == [Date(2018, 4, 30), Date(2018, 5, 31), Date(2018, 6, 30), Date(2018, 7, 31)]


def test_end_of_range_weeks():
    """Test end_of_range with week unit.
    """
    interval = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
    result = end_of_range(interval, 'week')
    assert result == [Date(2018, 1, 7), Date(2018, 1, 14), Date(2018, 1, 21), Date(2018, 1, 28)]


def test_end_of_range_leap_year():
    """Test end_of_range correctly handles February in leap year.
    """
    interval = Interval(Date(2020, 1, 15), Date(2020, 3, 15))
    result = end_of_range(interval, 'month')
    assert result == [Date(2020, 1, 31), Date(2020, 2, 29), Date(2020, 3, 31)]


def test_start_end_range_datetime():
    """Test start_of_range and end_of_range work with DateTime intervals.
    """
    interval = Interval(DateTime(2018, 1, 5, 10, 0, 0, tzinfo=EST),
                       DateTime(2018, 3, 5, 15, 0, 0, tzinfo=EST))
    
    start_result = start_of_range(interval, 'month')
    assert len(start_result) == 3
    assert all(isinstance(d, DateTime) for d in start_result)
    
    end_result = end_of_range(interval, 'month')
    assert len(end_result) == 3
    assert all(isinstance(d, DateTime) for d in end_result)


def test_create_ics():
    """Test create_ics function generates valid iCalendar format.
    """
    from date.date import create_ics
    
    begdate = DateTime(2024, 1, 15, 9, 30, 0, tzinfo=EST)
    enddate = DateTime(2024, 1, 15, 16, 0, 0, tzinfo=EST)
    summary = "Test Meeting"
    location = "Conference Room A"
    
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


if __name__ == '__main__':
    pytest.main([__file__])
