from __future__ import annotations

__version__ = '0.1.48'

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
    """Date for the calendar day year-month-day.
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
    tzinfo: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = UTC,
    fold: int = 0,
) -> DateTime:
    """DateTime for the given fields, in UTC unless tzinfo names a zone.

    Parameters
    ----------
    year : int
        Calendar year.
    month : int
        1-12.
    day : int
        Day of the month.
    hour : int, default 0
        0-23.
    minute : int, default 0
        0-59.
    second : int, default 0
        0-59.
    microsecond : int, default 0
        0-999999.
    tzinfo : str, tzinfo or None, default UTC
        A str is a zone name. None gives a naive DateTime, so only an
        explicit None matches `datetime.datetime`, whose default is naive.
    fold : int, default 0
        0 or 1: the earlier or later of the two wall times a
        daylight-saving fall-back repeats.

    Returns
    -------
    DateTime
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
        fold=fold)


def time(
    hour: int,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
    tzinfo: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = UTC,
) -> Time:
    """Time of day for the given fields, in UTC unless tzinfo names a zone.

    Parameters
    ----------
    hour : int
        0-23.
    minute : int, default 0
        0-59.
    second : int, default 0
        0-59.
    microsecond : int, default 0
        0-999999.
    tzinfo : str, tzinfo or None, default UTC
        A str is a zone name. None gives a naive Time, so only an explicit
        None matches `datetime.time`, whose default is naive.

    Returns
    -------
    Time
    """
    return Time(hour, minute, second, microsecond, tzinfo)


def interval(begdate: Date | DateTime, enddate: Date | DateTime) -> Interval:
    """Interval between two dates, its start the earlier of the two.
    """
    return Interval(begdate, enddate)


def parse(
    s: str | None,
    calendar: str | Calendar | None = None,
    raise_err: bool = False,
) -> DateTime | None:
    """DateTime that DateTime.parse reads from s.

    Parameters
    ----------
    s : str or None
        Text in any form DateTime.parse accepts, a date code such as 'T-3b'
        included.
    calendar : str, Calendar or None, default None
        Calendar that business-day codes count against. None takes the
        default calendar, where DateTime.parse itself defaults to 'NYSE'.
    raise_err : bool, default False
        True raises where s is None or does not parse. False returns None.

    Returns
    -------
    DateTime or None
        None where s is None or does not parse, and raise_err is False.

    Raises
    ------
    ValueError
        s is None or does not parse, and raise_err is True.
    """
    if calendar is None:
        calendar = get_default_calendar()
    return DateTime.parse(s, calendar=calendar, raise_err=raise_err)


def instance(
    obj: _datetime.date | _datetime.datetime | _datetime.time,
) -> DateTime | Date | Time:
    """The opendate counterpart of a stdlib date, datetime or time.

    Parameters
    ----------
    obj : datetime.date, datetime.datetime or datetime.time
        Stdlib value to wrap.

    Returns
    -------
    DateTime, Date or Time
        DateTime for a datetime, Date for a date, Time for a time.

    Raises
    ------
    ValueError
        obj is none of the three.
    """
    if isinstance(obj, _datetime.date) and not isinstance(obj, _datetime.datetime):
        return Date.instance(obj)
    if isinstance(obj, _datetime.time):
        return Time.instance(obj)
    if isinstance(obj, _datetime.datetime):
        return DateTime.instance(obj)
    raise ValueError(f'opendate `instance` helper cannot parse type {type(obj)}')


def now(tz: str | _zoneinfo.ZoneInfo | None = None) -> DateTime:
    """Current instant as a DateTime in tz, the local zone where tz is None.
    """
    return DateTime.now(tz)


def today(tz: str | _zoneinfo.ZoneInfo | None = None) -> DateTime:
    """Midnight today as a DateTime in tz, the local zone where tz is None.
    """
    return DateTime.today(tz)


__all__ = [
    'Date',
    'date',
    'DateTime',
    'datetime',
    'Calendar',
    'Timezone',
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
