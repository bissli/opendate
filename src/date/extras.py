from __future__ import annotations

"""Legacy compatibility functions for OpenDate.

This module contains functions that exist primarily for backward compatibility
with older codebases. These functions provide alternative interfaces to
functionality that may be available through other means in the core Date,
DateTime, and Interval classes.

New code should prefer using the built-in methods on Date, DateTime, and
Interval objects where applicable.
"""

from date.calendars import Calendar, get_calendar
from date.date_ import Date
from date.datetime_ import DateTime
from date.interval import Interval

__all__ = [
    'is_within_business_hours',
    'is_business_day',
    'overlap_days',
    'create_ics',
]


def is_within_business_hours(calendar: str | Calendar = 'NYSE') -> bool:
    """Return whether the current native datetime is between open and close of business hours.
    """
    if isinstance(calendar, str):
        calendar = get_calendar(calendar)
    this = DateTime.now()
    this_cal = this.in_tz(calendar.tz).calendar(calendar)
    bounds = this_cal.business_hours()
    return this_cal.business_open() and (bounds[0] <= this.astimezone(calendar.tz) <= bounds[1])


def is_business_day(calendar: str | Calendar = 'NYSE') -> bool:
    """Return whether the current native datetime is a business day.
    """
    if isinstance(calendar, str):
        calendar = get_calendar(calendar)
    return DateTime.now(tz=calendar.tz).calendar(calendar).is_business_day()


def overlap_days(
    interval_one: Interval | tuple[Date | DateTime, Date | DateTime],
    interval_two: Interval | tuple[Date | DateTime, Date | DateTime],
    days: bool = False,
) -> bool | int:
    """Calculate how much two date intervals overlap.

    When days=False, returns True/False indicating whether intervals overlap.
    When days=True, returns the actual day count (negative if non-overlapping).

    Algorithm adapted from Raymond Hettinger: http://stackoverflow.com/a/9044111
    """
    if not isinstance(interval_one, Interval):
        interval_one = Interval(*interval_one)
    if not isinstance(interval_two, Interval):
        interval_two = Interval(*interval_two)

    latest_start = max(interval_one.start, interval_two.start)
    earliest_end = min(interval_one.end, interval_two.end)
    overlap = (earliest_end - latest_start).days + 1
    if days:
        return overlap
    return overlap >= 0


def create_ics(begdate: Date | DateTime, enddate: Date | DateTime, summary: str, location: str) -> str:
    """Create a simple .ics file per RFC 5545 guidelines."""

    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//hacksw/handcal//NONSGML v1.0//EN
BEGIN:VEVENT
DTSTART;TZID=America/New_York:{begdate:%Y%m%dT%H%M%S}
DTEND;TZID=America/New_York:{enddate:%Y%m%dT%H%M%S}
SUMMARY:{summary}
LOCATION:{location}
END:VEVENT
END:VCALENDAR
    """
