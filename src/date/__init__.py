from __future__ import annotations

__version__ = '0.1.27'

import datetime as _datetime
import zoneinfo as _zoneinfo

from date.date import EST, GMT, LCL, UTC, WEEKDAY_SHORTNAME, Calendar
from date.date import CustomCalendar, Date, DateTime, ExchangeCalendar
from date.date import Interval, Time, Timezone, WeekDay, available_calendars
from date.date import expect_date, expect_date_or_datetime, expect_datetime
from date.date import expect_native_timezone, expect_time, expect_utc_timezone
from date.date import get_calendar, prefer_native_timezone
from date.date import prefer_utc_timezone, register_calendar
from date.extras import create_ics, is_business_day, is_within_business_hours
from date.extras import overlap_days

timezone = Timezone


def date(year: int, month: int, day: int) -> Date:
    """Create new Date
    """
    return Date(year, month, day)


def datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
    tzinfo: str | float | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = UTC,
    fold: int = 0,
) -> DateTime:
    """Create new DateTime
    """
    return DateTime(
        year,
        month,
        day,
        hour=hour,
        minute=minute,
        second=second,
        microsecond=microsecond,
        tzinfo=tzinfo,
        fold=fold,
    )


def time(
    hour: int,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
    tzinfo: str | float | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = UTC,
) -> Time:
    """Create new Time
    """
    return Time(hour, minute, second, microsecond, tzinfo)


def interval(begdate: Date | DateTime, enddate: Date | DateTime) -> Interval:
    """Create new Interval
    """
    return Interval(begdate, enddate)


def parse(s: str | None, calendar: str | Calendar = 'NYSE', raise_err: bool = False) -> DateTime | None:
    """Parse using DateTime.parse
    """
    return DateTime.parse(s, calendar=calendar, raise_err=raise_err)


def instance(obj: _datetime.date | _datetime.datetime | _datetime.time) -> DateTime | Date | Time:
    """Create a DateTime/Date/Time instance from a datetime/date/time native one.
    """
    if isinstance(obj, _datetime.date) and not isinstance(obj, _datetime.datetime):
        return Date.instance(obj)
    if isinstance(obj, _datetime.time):
        return Time.instance(obj)
    if isinstance(obj, _datetime.datetime):
        return DateTime.instance(obj)
    raise ValueError(f'opendate `instance` helper cannot parse type {type(obj)}')


def now(tz: str | _zoneinfo.ZoneInfo | None = None) -> DateTime:
    """Returns Datetime.now
    """
    return DateTime.now(tz)


def today(tz: str | _zoneinfo.ZoneInfo | None = None) -> DateTime:
    """Returns DateTime.today
    """
    return DateTime.today(tz)


__all__ = [
    'Date',
    'date',
    'DateTime',
    'datetime',
    'Calendar',
    'ExchangeCalendar',
    'CustomCalendar',
    'get_calendar',
    'available_calendars',
    'register_calendar',
    'expect_date',
    'expect_datetime',
    'expect_time',
    'expect_date_or_datetime',
    'expect_native_timezone',
    'expect_utc_timezone',
    'instance',
    'Interval',
    'interval',
    'is_business_day',
    'is_within_business_hours',
    'LCL',
    'now',
    'overlap_days',
    'parse',
    'prefer_native_timezone',
    'prefer_utc_timezone',
    'Time',
    'time',
    'timezone',
    'today',
    'WeekDay',
    'EST',
    'GMT',
    'UTC',
    'WEEKDAY_SHORTNAME',
    'create_ics',
    ]
