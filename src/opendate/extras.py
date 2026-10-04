"""Legacy compatibility functions for OpenDate.

New code should prefer the methods on Date, DateTime and Interval where
one exists.
"""
from __future__ import annotations

from opendate.calendars import Calendar, get_calendar, get_default_calendar
from opendate.date_ import Date
from opendate.datetime_ import DateTime
from opendate.interval import Interval

__all__ = [
    'is_within_business_hours',
    'is_business_day',
    'overlap_days',
    'create_ics',
]


def is_within_business_hours(calendar: str | Calendar | None = None) -> bool:
    """True where now falls within the calendar's business hours today.

    Parameters
    ----------
    calendar : str, Calendar or None, default None
        Calendar, or its name, whose zone and hours apply. None takes the
        default calendar.

    Returns
    -------
    bool
        False on a day the calendar is closed, whatever the hour.
    """
    if calendar is None:
        calendar = get_default_calendar()
    if isinstance(calendar, str):
        calendar = get_calendar(calendar)
    this = DateTime.now()
    this_cal = this.in_tz(calendar.tz).calendar(calendar)
    bounds = this_cal.business_hours()
    return this_cal.business_open() and (
        bounds[0] <= this.astimezone(calendar.tz) <= bounds[1])


def is_business_day(calendar: str | Calendar | None = None) -> bool:
    """Return whether the current native datetime is a business day.
    """
    if calendar is None:
        calendar = get_default_calendar()
    if isinstance(calendar, str):
        calendar = get_calendar(calendar)
    return DateTime.now(tz=calendar.tz).calendar(calendar).is_business_day()


def overlap_days(
    interval_one: Interval | tuple[Date | DateTime, Date | DateTime],
    interval_two: Interval | tuple[Date | DateTime, Date | DateTime],
    days: bool = False,
) -> bool | int:
    """Whether, or by how many days, two date intervals overlap.

    Parameters
    ----------
    interval_one : Interval or tuple of (start, end)
        First interval. A tuple is read as Interval(start, end).
    interval_two : Interval or tuple of (start, end)
        Second interval, read the same way.
    days : bool, default False
        True returns the day count, False whether the count is >= 0.

    Returns
    -------
    bool or int
        With both endpoints counted::

            overlap = (min(end_1, end_2) - max(start_1, start_2)).days + 1

        Negative where the intervals are apart. Zero, and so True, where
        one ends the day before the other starts.

    References
    ----------
    - Raymond Hettinger, http://stackoverflow.com/a/9044111
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


def create_ics(
    begdate: Date | DateTime,
    enddate: Date | DateTime,
    summary: str,
    location: str,
) -> str:
    """Text of a one-event iCalendar file per RFC 5545.

    Parameters
    ----------
    begdate : Date or DateTime
        Event start. Its wall time is written under
        TZID=America/New_York whatever its own zone, and a Date is
        written as midnight.
    enddate : Date or DateTime
        Event end, written the same way.
    summary : str
        SUMMARY line text, written unescaped.
    location : str
        LOCATION line text, written unescaped.

    Returns
    -------
    str
        The VCALENDAR text. Nothing is written to disk.
    """
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
