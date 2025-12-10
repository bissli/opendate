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

        if methods_to_wrap:
            # Identify which bases are pendulum classes (we want to wrap their methods)
            pendulum_bases = tuple(
                base for base in bases
                if issubclass(base, (_pendulum.Date, _pendulum.DateTime))
            )

            for method_name in methods_to_wrap:
                # Skip if method is already explicitly defined in namespace
                if method_name in namespace:
                    continue

                # Check if any NON-pendulum base class has this method defined
                # (i.e., our mixins like DateBusinessMixin have explicit overrides)
                explicitly_defined = False
                for base in bases:
                    if base in pendulum_bases:
                        continue  # Skip pendulum classes
                    if method_name in base.__dict__:
                        explicitly_defined = True
                        break

                if explicitly_defined:
                    continue

                # Find the method in pendulum base classes and wrap it
                for base in pendulum_bases:
                    if hasattr(base, method_name):
                        original = getattr(base, method_name)
                        if callable(original):
                            wrapped = _make_context_preserver(original, cls)
                            setattr(cls, method_name, wrapped)
                        break

        return cls
