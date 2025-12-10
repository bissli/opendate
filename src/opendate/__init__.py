from __future__ import annotations

__version__ = '0.1.34'

import datetime as _datetime
import zoneinfo as _zoneinfo

from opendate.calendars import Calendar, CustomCalendar, ExchangeCalendar
from opendate.calendars import available_calendars, get_calendar
from opendate.calendars import get_default_calendar, register_calendar
from opendate.calendars import set_default_calendar
from opendate.constants import EST, GMT, LCL, UTC, WEEKDAY_SHORTNAME, Timezone
from opendate.constants import WeekDay
from opendate.date_ import Date
from opendate.datetime_ import DateTime
from opendate.decorators import expect_date, expect_date_or_datetime
from opendate.decorators import expect_datetime, expect_native_timezone
from opendate.decorators import expect_time, expect_utc_timezone
from opendate.decorators import prefer_native_timezone, prefer_utc_timezone
from opendate.extras import create_ics, is_business_day
from opendate.extras import is_within_business_hours, overlap_days
from opendate.interval import Interval
from opendate.time_ import Time

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


def parse(s: str | None, calendar: str | Calendar | None = None, raise_err: bool = False) -> DateTime | None:
    """Parse using DateTime.parse
    """
    if calendar is None:
        calendar = get_default_calendar()
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
    'get_default_calendar',
    'set_default_calendar',
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
