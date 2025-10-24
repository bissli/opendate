from unittest.mock import patch

import pytest

from date import EST, NYSE, Date, DateTime
from date.extras import is_within_business_hours, overlap_days


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


def test_create_ics():
    """Test create_ics function generates valid iCalendar format."""
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
