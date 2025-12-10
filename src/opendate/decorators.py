from __future__ import annotations

import datetime as _datetime
from collections.abc import Callable, Sequence
from functools import partial, wraps
from typing import Any

import numpy as np
import pandas as pd
import pendulum as _pendulum

from opendate.constants import LCL, UTC
from opendate.helpers import isdateish


def parse_arg(typ: type | str, arg: Any) -> Any:
    """Parse argument to specified type or 'smart' to preserve Date/DateTime.
    """
    import opendate

    if not isdateish(arg):
        return arg

    if typ == 'smart':
        if isinstance(arg, (opendate.Date, opendate.DateTime)):
            return arg
        if isinstance(arg, (_datetime.datetime, _pendulum.DateTime)):
            return opendate.DateTime.instance(arg)
        if isinstance(arg, pd.Timestamp):
            if pd.isna(arg):
                return None
            return opendate.DateTime.instance(arg)
        if isinstance(arg, np.datetime64):
            if np.isnat(arg):
                return None
            return opendate.DateTime.instance(arg)
        if isinstance(arg, _datetime.date):
            return opendate.Date.instance(arg)
        if isinstance(arg, _datetime.time):
            return opendate.Time.instance(arg)
        return arg

    if typ == _datetime.datetime:
        return opendate.DateTime.instance(arg)
    if typ == _datetime.date:
        return opendate.Date.instance(arg)
    if typ == _datetime.time:
        return opendate.Time.instance(arg)
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
    import opendate

    if isinstance(typ, str):
        if typ == 'Date':
            return opendate.Date
        if typ == 'DateTime':
            return opendate.DateTime
        if typ == 'Interval':
            return opendate.Interval
    if typ:
        return typ
    if obj.__class__.__name__ == 'Interval':
        return opendate.Interval
    if obj.__class__ in {_datetime.datetime, _pendulum.DateTime} or obj.__class__.__name__ == 'DateTime':
        return opendate.DateTime
    if obj.__class__ in {_datetime.date, _pendulum.Date} or obj.__class__.__name__ == 'Date':
        return opendate.Date
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
        import opendate

        if len(args) >= 3:
            cls_or_self, begdate, enddate = args[0], args[1], args[2]
            rest_args = args[3:]

            tz = UTC
            if isinstance(begdate, opendate.DateTime) and begdate.tzinfo:
                tz = begdate.tzinfo
            elif isinstance(enddate, opendate.DateTime) and enddate.tzinfo:
                tz = enddate.tzinfo

            if isinstance(begdate, opendate.Date) and not isinstance(begdate, opendate.DateTime):
                if isinstance(enddate, opendate.DateTime):
                    begdate = opendate.DateTime(begdate.year, begdate.month, begdate.day, tzinfo=tz)
            elif isinstance(enddate, opendate.Date) and not isinstance(enddate, opendate.DateTime):
                if isinstance(begdate, opendate.DateTime):
                    enddate = opendate.DateTime(enddate.year, enddate.month, enddate.day, tzinfo=tz)

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
