"""Metaclass for automatic context preservation on pendulum methods.
"""
from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

import pendulum as _pendulum

if TYPE_CHECKING:
    from opendate.calendars import Calendar

DATE_METHODS_RETURNING_DATE = {
    'add',
    'subtract',
    'replace',
    'set',
    'average',
    'closest',
    'farthest',
    'end_of',
    'start_of',
    'first_of',
    'last_of',
    'next',
    'previous',
    'nth_of',
    }

DATETIME_METHODS_RETURNING_DATETIME = DATE_METHODS_RETURNING_DATE | {
    'at',
    'on',
    'naive',
    'astimezone',
    'in_timezone',
    'in_tz',
    }

METHODS_RETURNING_INTERVAL = {
    'diff',
    '__sub__',
    }


def _make_context_preserver(
    original_method: Callable[..., Any],
    target_cls: type,
) -> Callable[..., Any]:
    """Wrap a pendulum method so a date result keeps the caller's _calendar.

    Parameters
    ----------
    original_method : Callable
        Pendulum method to wrap.
    target_cls : type
        Date or DateTime class a pendulum Date or DateTime result is
        rebuilt as.

    Returns
    -------
    Callable
        Wrapper returning original_method's result, rebuilt as target_cls
        and carrying self's _calendar where it is a Date or DateTime, else
        unchanged.
    """
    @wraps(original_method)
    def wrapper(self, *args, **kwargs):
        _calendar: Calendar | None = getattr(self, '_calendar', None)
        result = original_method(self, *args, **kwargs)

        if isinstance(result, (_pendulum.Date, _pendulum.DateTime)):
            if not isinstance(result, target_cls):
                result = target_cls.instance(result)
            if hasattr(result, '_calendar'):
                result._calendar = _calendar
        return result
    return wrapper


def _make_interval_wrapper(
    original_method: Callable[..., Any],
    target_cls: type,
) -> Callable[..., Any]:
    """Wrap a pendulum method so an Interval result is an opendate Interval.

    Parameters
    ----------
    original_method : Callable
        Pendulum method to wrap.
    target_cls : type
        Date or DateTime class a pendulum Date or DateTime result is
        rebuilt as.

    Returns
    -------
    Callable
        Wrapper returning a pendulum Interval as an opendate Interval, and
        a Date or DateTime as target_cls, each carrying self's _calendar.
    """
    @wraps(original_method)
    def wrapper(self, *args, **kwargs):
        # Circular import: opendate.interval imports the modules that
        # import this one.
        from opendate.interval import Interval

        _calendar: Calendar | None = getattr(self, '_calendar', None)
        result = original_method(self, *args, **kwargs)

        if isinstance(result, _pendulum.Interval) and not isinstance(result, Interval):
            result = Interval(result.start, result.end)
            if _calendar:
                result._calendar = _calendar
        elif isinstance(result, (_pendulum.Date, _pendulum.DateTime)):
            if not isinstance(result, target_cls):
                result = target_cls.instance(result)
            if hasattr(result, '_calendar'):
                result._calendar = _calendar
        return result
    return wrapper


class DateContextMeta(type):
    """Metaclass that wraps pendulum methods so their results keep _calendar.

    Parameters
    ----------
    methods_to_wrap : set[str] or None, default None
        Pendulum methods returning a Date or DateTime, wrapped so the result
        is an instance of the new class carrying the caller's _calendar.
        `diff` and `__sub__` are wrapped too, to return an opendate
        Interval. A method the class or a non-pendulum base such as
        DateBusinessMixin defines is never wrapped, so the override wins.

    Examples
    --------
    ::

        class Date(
            DateBusinessMixin,
            _pendulum.Date,
            metaclass=DateContextMeta,
            methods_to_wrap=DATE_METHODS_RETURNING_DATE):
            pass
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        methods_to_wrap: set[str] | None = None,
        **kwargs: Any,
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        pendulum_bases = tuple(
            base for base in bases
            if issubclass(base, (_pendulum.Date, _pendulum.DateTime)))

        def _is_explicitly_defined(method_name: str) -> bool:
            """True where the class or a non-pendulum base defines it.
            """
            if method_name in namespace:
                return True
            for base in bases:
                if base in pendulum_bases:
                    continue
                if method_name in base.__dict__:
                    return True
            return False

        def _wrap_method(
            method_name: str,
            wrapper_fn: Callable[[Callable[..., Any], type], Callable[..., Any]],
        ) -> None:
            """Set on cls the first pendulum base's method_name, wrapped.
            """
            for base in pendulum_bases:
                if hasattr(base, method_name):
                    original = getattr(base, method_name)
                    if callable(original):
                        wrapped = wrapper_fn(original, cls)
                        setattr(cls, method_name, wrapped)
                    break

        if methods_to_wrap:
            for method_name in methods_to_wrap:
                if not _is_explicitly_defined(method_name):
                    _wrap_method(method_name, _make_context_preserver)

        for method_name in METHODS_RETURNING_INTERVAL:
            if not _is_explicitly_defined(method_name):
                _wrap_method(method_name, _make_interval_wrapper)

        return cls
