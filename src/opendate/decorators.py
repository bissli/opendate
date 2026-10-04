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
    """arg as an opendate type chosen by typ, or unchanged if not date-like.

    Parameters
    ----------
    typ : type or str
        datetime.datetime, datetime.date or datetime.time converts arg to
        DateTime, Date or Time. 'smart' picks by arg's own kind and keeps
        an opendate Date or DateTime as it is. Any other value returns arg.
    arg : Any
        Value to convert.

    Returns
    -------
    Any
        The converted value. In 'smart' mode a NaT pandas Timestamp or
        numpy datetime64 gives None.
    """
    # Circular import: opendate imports this module.
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
    """Each of args converted by parse_arg, recursing into sequences.

    Parameters
    ----------
    typ : type or str
        As in parse_arg.
    *args : Any
        Values to convert. A non-str sequence comes back as a list of its
        converted items.

    Returns
    -------
    list
        Converted args, in order.
    """
    this = []
    for a in args:
        if isinstance(a, Sequence) and not isinstance(a, str):
            this.append(parse_args(typ, *a))
        else:
            this.append(parse_arg(typ, a))
    return this


def expect(
    func: Callable[..., Any] | None = None,
    *,
    typ: type[_datetime.date] | str | None = None,
    exclkw: bool = False,
) -> Callable:
    """Decorate func so its date-like arguments arrive as opendate types.

    Parameters
    ----------
    func : Callable or None, default None
        Function to wrap. None returns a decorator that takes it.
    typ : type, str or None, default None
        datetime.date, datetime.datetime or datetime.time converts every
        date-like argument to Date, DateTime or Time. 'smart' keeps each
        argument's own kind, as parse_arg describes.
    exclkw : bool, default False
        True leaves keyword arguments unconverted.

    Returns
    -------
    Callable
        Wrapped function, or the decorator where func is None.
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


def type_class(typ: type | str | None, obj: Any) -> type:
    """Class a store_calendar result is rebuilt as.

    Parameters
    ----------
    typ : type, str or None
        A class, or 'Date', 'DateTime' or 'Interval' naming one. Any other
        truthy value comes back as it is. None picks the class from obj.
    obj : Any
        Value whose class picks the result where typ is None.

    Returns
    -------
    type
        opendate Date, DateTime or Interval, or typ itself.

    Raises
    ------
    ValueError
        typ is None and obj is no stdlib, pendulum or opendate date,
        datetime or Interval.
    """
    # Circular import: opendate imports this module.
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
    if (obj.__class__ in {_datetime.datetime, _pendulum.DateTime}
        or obj.__class__.__name__ == 'DateTime'):
        return opendate.DateTime
    if (obj.__class__ in {_datetime.date, _pendulum.Date}
        or obj.__class__.__name__ == 'Date'):
        return opendate.Date
    raise ValueError(f'Unknown type {typ}')


def store_calendar(
    func: Callable[..., Any] | None = None,
    *,
    typ: type | str | None = None,
) -> Callable:
    """Decorate a method so its result keeps self's _calendar.

    Parameters
    ----------
    func : Callable or None, default None
        Method to wrap. None returns a decorator that takes it, for the
        `@store_calendar(typ=...)` form.
    typ : type, str or None, default None
        Class the result is rebuilt as, resolved by type_class. None takes
        the class from self.

    Returns
    -------
    Callable
        Wrapped method, or the decorator where func is None.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _calendar = self._calendar
        d = type_class(typ, self).instance(func(self, *args, **kwargs))
        if d is not None:
            d._calendar = _calendar
        return d
    if func is None:
        return partial(store_calendar, typ=typ)
    return wrapper


def reset_business(func: Callable[..., Any]) -> Callable:
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


def normalize_date_datetime_pairs(func: Callable[..., Any]) -> Callable:
    """Decorate func so a mixed Date/DateTime pair arrives as two DateTimes.

    Parameters
    ----------
    func : Callable
        Function or method whose second and third positional arguments are
        the pair. A pair passed by keyword is left as it is.

    Returns
    -------
    Callable
        Wrapper that lifts the Date of a mixed pair to a DateTime at
        midnight in the other's zone, or in UTC where that one is naive.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Circular import: opendate imports this module.
        import opendate

        if len(args) >= 3:
            cls_or_self, begdate, enddate = args[0], args[1], args[2]
            rest_args = args[3:]

            tz = UTC
            if isinstance(begdate, opendate.DateTime) and begdate.tzinfo:
                tz = begdate.tzinfo
            elif isinstance(enddate, opendate.DateTime) and enddate.tzinfo:
                tz = enddate.tzinfo

            if (isinstance(begdate, opendate.Date)
                and not isinstance(begdate, opendate.DateTime)):
                if isinstance(enddate, opendate.DateTime):
                    begdate = opendate.DateTime(
                        begdate.year,
                        begdate.month,
                        begdate.day,
                        tzinfo=tz)
            elif (isinstance(enddate, opendate.Date)
                and not isinstance(enddate, opendate.DateTime)):
                if isinstance(begdate, opendate.DateTime):
                    enddate = opendate.DateTime(
                        enddate.year,
                        enddate.month,
                        enddate.day,
                        tzinfo=tz)

            args = (cls_or_self, begdate, enddate) + rest_args

        return func(*args, **kwargs)
    return wrapper


def prefer_utc_timezone(func: Callable[..., Any], force: bool = False) -> Callable:
    """Decorate func so a naive result comes back stamped UTC.

    Parameters
    ----------
    func : Callable
        Function returning a datetime-like value or None.
    force : bool, default False
        True stamps UTC on an aware result too, replacing its zone without
        converting the wall time.

    Returns
    -------
    Callable
        Wrapper returning None for a falsy result, else the result with
        its tzinfo replaced by UTC where it was naive or force is True.
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


def prefer_native_timezone(func: Callable[..., Any], force: bool = False) -> Callable:
    """Decorate func so a naive result comes back stamped with the local zone.

    Parameters
    ----------
    func : Callable
        Function returning a datetime-like value or None.
    force : bool, default False
        True stamps the local zone on an aware result too, replacing its
        zone without converting the wall time.

    Returns
    -------
    Callable
        Wrapper returning None for a falsy result, else the result with
        its tzinfo replaced by LCL where it was naive or force is True.
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
