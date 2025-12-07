from __future__ import annotations

import datetime as _datetime
from collections.abc import Callable, Sequence
from functools import partial, wraps
from typing import Any

import numpy as np
import pandas as pd
import pendulum as _pendulum

from date.constants import LCL, UTC
from date.helpers import isdateish


def parse_arg(typ: type | str, arg: Any) -> Any:
    """Parse argument to specified type or 'smart' to preserve Date/DateTime.
    """
    import date

    if not isdateish(arg):
        return arg

    if typ == 'smart':
        if isinstance(arg, (date.Date, date.DateTime)):
            return arg
        if isinstance(arg, (_datetime.datetime, _pendulum.DateTime)):
            return date.DateTime.instance(arg)
        if isinstance(arg, pd.Timestamp):
            if pd.isna(arg):
                return None
            return date.DateTime.instance(arg)
        if isinstance(arg, np.datetime64):
            if np.isnat(arg):
                return None
            return date.DateTime.instance(arg)
        if isinstance(arg, _datetime.date):
            return date.Date.instance(arg)
        if isinstance(arg, _datetime.time):
            return date.Time.instance(arg)
        return arg

    if typ == _datetime.datetime:
        return date.DateTime.instance(arg)
    if typ == _datetime.date:
        return date.Date.instance(arg)
    if typ == _datetime.time:
        return date.Time.instance(arg)
    return arg


def parse_args(typ: type | str, *args: Any) -> list[Any]:
    """Parse args to specified type or 'smart' mode.
    """
    this = []
    for a in args:
        if isinstance(a, Sequence) and not isinstance(a, str):
            this.append(parse_args(typ, *a))
        else:
            this.append(parse_arg(typ, a))
    return this


def expect(func=None, *, typ: type[_datetime.date] | str = None, exclkw: bool = False) -> Callable:
    """Decorator to force input type of date/datetime inputs.

    typ can be _datetime.date, _datetime.datetime, _datetime.time, or 'smart'
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            args = parse_args(typ, *args)
            if not exclkw:
                for k, v in kwargs.items():
                    if isdateish(v):
                        kwargs[k] = parse_arg(typ, v)
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    return decorator(func)


expect_date = partial(expect, typ=_datetime.date)
expect_datetime = partial(expect, typ=_datetime.datetime)
expect_time = partial(expect, typ=_datetime.time)
expect_date_or_datetime = partial(expect, typ='smart')


def type_class(typ, obj):
    """Get the appropriate class for the type/object combination."""
    import date

    if isinstance(typ, str):
        if typ == 'Date':
            return date.Date
        if typ == 'DateTime':
            return date.DateTime
        if typ == 'Interval':
            return date.Interval
    if typ:
        return typ
    if obj.__class__.__name__ == 'Interval':
        return date.Interval
    if obj.__class__ in {_datetime.datetime, _pendulum.DateTime} or obj.__class__.__name__ == 'DateTime':
        return date.DateTime
    if obj.__class__ in {_datetime.date, _pendulum.Date} or obj.__class__.__name__ == 'Date':
        return date.Date
    raise ValueError(f'Unknown type {typ}')


def store_calendar(func=None, *, typ=None):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _calendar = self._calendar
        d = type_class(typ, self).instance(func(self, *args, **kwargs))
        d._calendar = _calendar
        return d
    if func is None:
        return partial(store_calendar, typ=typ)
    return wrapper


def store_both(func=None, *, typ=None):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _calendar = self._calendar
        _business = self._business
        d = type_class(typ, self).instance(func(self, *args, **kwargs))
        d._calendar = _calendar
        d._business = _business
        return d
    if func is None:
        return partial(store_both, typ=typ)
    return wrapper


def reset_business(func):
    """Decorator to reset business mode after function execution.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            self._business = False
            self._start._business = False
            self._end._business = False
    return wrapper


def normalize_date_datetime_pairs(func):
    """Decorator to normalize mixed Date/DateTime pairs to DateTime.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        import date

        if len(args) >= 3:
            cls_or_self, begdate, enddate = args[0], args[1], args[2]
            rest_args = args[3:]

            tz = UTC
            if isinstance(begdate, date.DateTime) and begdate.tzinfo:
                tz = begdate.tzinfo
            elif isinstance(enddate, date.DateTime) and enddate.tzinfo:
                tz = enddate.tzinfo

            if isinstance(begdate, date.Date) and not isinstance(begdate, date.DateTime):
                if isinstance(enddate, date.DateTime):
                    begdate = date.DateTime(begdate.year, begdate.month, begdate.day, tzinfo=tz)
            elif isinstance(enddate, date.Date) and not isinstance(enddate, date.DateTime):
                if isinstance(begdate, date.DateTime):
                    enddate = date.DateTime(enddate.year, enddate.month, enddate.day, tzinfo=tz)

            args = (cls_or_self, begdate, enddate) + rest_args

        return func(*args, **kwargs)
    return wrapper


def prefer_utc_timezone(func, force: bool = False) -> Callable:
    """Return datetime as UTC.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        d = func(*args, **kwargs)
        if not d:
            return
        if not force and d.tzinfo:
            return d
        return d.replace(tzinfo=UTC)
    return wrapper


def prefer_native_timezone(func, force: bool = False) -> Callable:
    """Return datetime as native.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        d = func(*args, **kwargs)
        if not d:
            return
        if not force and d.tzinfo:
            return d
        return d.replace(tzinfo=LCL)
    return wrapper


expect_native_timezone = partial(prefer_native_timezone, force=True)
expect_utc_timezone = partial(prefer_utc_timezone, force=True)
