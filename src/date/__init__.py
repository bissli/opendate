__version__ = '0.1.3'

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
from date.date import IntervalError
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
from date.date import expect_native_timezone
from date.date import expect_utc_timezone
from date.date import prefer_native_timezone
from date.date import prefer_utc_timezone
from date.date import Timezone
from date.extras import overlap_days
from date.extras import is_business_day
from date.extras import is_within_business_hours


timezone = Timezone


def date(*args, **kwargs):
    return Date(*args, **kwargs)


def datetime(*args, **kwargs):
    return DateTime(*args, **kwargs)


def time(*args, **kwargs):
    return Time(*args, **kwargs)


def parse():
    """Generic parser that guesses type"""
    raise NotImplementedError(
        'Generic parser not implemented, use Date or DateTime parsers'
    )


def instance(obj: _datetime.date | _datetime.datetime | _datetime.time) -> DateTime | Date | Time:
    """Create a DateTime/Date/Time instance from a datetime/date/time native one.
    """
    if isinstance(obj, DateTime | Date | Time):
        return obj
    if isinstance(obj, _datetime.date) and not isinstance(obj, _datetime.datetime):
        return Date.instance(obj)
    if isinstance(obj, _datetime.time):
        return Time.instance(obj)
    if isinstance(obj, _datetime.datetime):
        return DateTime.instance(obj)


def now(tz: str | _zoneinfo.ZoneInfo | None = None) -> DateTime:
    """Get current datetime
    """
    return DateTime.now(tz)


def today(tz: str | _zoneinfo.ZoneInfo = None) -> DateTime:
    """Get current date
    """
    return DateTime.today(tz)


__all__ = [
    'Date',
    'DateTime',
    'Interval',
    'IntervalError',
    'Time',
    'WeekDay',
    'now',
    'today',
    'parse',
    'LCL',
    'timezone',
    'expect_native_timezone',
    'expect_utc_timezone',
    'prefer_native_timezone',
    'prefer_utc_timezone',
    'expect_date',
    'expect_datetime',
    'Entity',
    'NYSE',
    'date',
    'datetime',
    'time',
    'overlap_days',
    'is_within_business_hours',
    'is_business_day',
    ]
