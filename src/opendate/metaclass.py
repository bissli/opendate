"""Metaclass for automatic context preservation on pendulum methods.

This module provides a metaclass that automatically wraps pendulum methods
to preserve the _calendar attribute when they return new Date/DateTime objects.
This ensures users don't accidentally lose business context when calling
pendulum methods that aren't explicitly overridden.
"""
from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

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


def _make_context_preserver(original_method, target_cls):
    """Create a wrapper that preserves _calendar context.

    Parameters
        original_method: The original pendulum method
        target_cls: The target class (Date or DateTime) for instance creation
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


def _make_interval_wrapper(original_method, target_cls):
    """Create a wrapper that converts pendulum.Interval to opendate.Interval.

    Parameters
        original_method: The original pendulum method
        target_cls: The target class (Date or DateTime) for context
    """
    @wraps(original_method)
    def wrapper(self, *args, **kwargs):
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
    """Metaclass that auto-wraps pendulum methods to preserve context.

    When a class is created with this metaclass, it automatically wraps
    specified pendulum methods to preserve the _calendar attribute.

    Usage:
        class Date(
            DateBusinessMixin,
            _pendulum.Date,
            metaclass=DateContextMeta,
            methods_to_wrap=DATE_METHODS_RETURNING_DATE
        ):
            pass

    The metaclass will NOT wrap methods that are already defined in the
    class namespace - explicit overrides (like those in DateBusinessMixin)
    take precedence.
    """

    def __new__(mcs, name, bases, namespace, methods_to_wrap=None, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        pendulum_bases = tuple(
            base for base in bases
            if issubclass(base, (_pendulum.Date, _pendulum.DateTime))
        )

        def _is_explicitly_defined(method_name):
            if method_name in namespace:
                return True
            for base in bases:
                if base in pendulum_bases:
                    continue
                if method_name in base.__dict__:
                    return True
            return False

        def _wrap_method(method_name, wrapper_fn):
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
