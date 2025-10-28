__version__ = '0.1.20'

import datetime as _datetime

import numpy as np
import pandas as pd
import pendulum as _pendulum
import zoneinfo as _zoneinfo

from typing_extensions import Optional
from typing_extensions import Union
from typing_extensions import overload

from date.date import Date
from date.date import DateTime
from date.date import Entity
from date.date import Interval
from date.date import LCL
from date.date import EST
from date.date import GMT
from date.date import UTC
from date.date import NYSE
from date.date import Time
from date.date import WeekDay
from date.date import WEEKDAY_SHORTNAME
from date.date import expect_date
from date.date import expect_datetime
from date.date import expect_time
from date.date import expect_date_or_datetime
from date.date import expect_native_timezone
from date.date import expect_utc_timezone
from date.date import prefer_native_timezone
from date.date import prefer_utc_timezone
from date.date import Timezone
from date.extras import create_ics 
from date.extras import is_business_day
from date.extras import is_within_business_hours
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
    tzinfo: str | float | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = UTC,  # note that this is different from our DateTime
    fold: int = 0,  # different from pendulum
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
    tzinfo: str | float | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = UTC,  # review this choice
) -> Time:
    """Create new Time
    """
    return Time(hour, minute, second, microsecond, tzinfo)


def interval(self, begdate: Date | DateTime, enddate: Date | DateTime):
    """Create new Interval
    """
    return Interval(begdate, enddate)


def parse(s: str | None, fmt: str = None, entity: Entity = NYSE, raise_err: bool = False) -> DateTime | None:
    """Parse using DateTime.parse
    """
    return DateTime.parse(s, entity=entity, raise_err=True)


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


def today(tz: str | _zoneinfo.ZoneInfo = None) -> DateTime:
    """Returns DateTime.today
    """
    return DateTime.today(tz)


__all__ = [
    'Date',
    'date',
    'DateTime',
    'datetime',
    'Entity',
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
    'NYSE',
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
