from __future__ import annotations

import contextlib
import datetime as _datetime
import sys
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pendulum as _pendulum

from date.constants import _IS_WINDOWS, DATEMATCH, LCL, UTC
from date.decorators import store_calendar
from date.helpers import _rust_parse_datetime
from date.mixins import DateBusinessMixin, DateExtrasMixin

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from date.calendars import Calendar


class Date(DateExtrasMixin, DateBusinessMixin, _pendulum.Date):
    """Date class extending pendulum.Date with business day and additional functionality.

    This class inherits all pendulum.Date functionality while adding:
    - Business day calculations with NYSE calendar integration
    - Additional date navigation methods
    - Enhanced parsing capabilities
    - Custom financial date utilities

    Unlike pendulum.Date, methods that create new instances return Date objects
    that preserve business status and entity association when chained.
    """

    def to_string(self, fmt: str) -> str:
        """Format date to string, handling platform-specific format codes.

        Automatically converts '%-' format codes to '%#' on Windows.
        """
        return self.strftime(fmt.replace('%-', '%#') if _IS_WINDOWS else fmt)

    @store_calendar(typ='Date')
    def replace(self, *args, **kwargs):
        """Replace method that preserves entity and business status.
        """
        return _pendulum.Date.replace(self, *args, **kwargs)

    @store_calendar(typ='Date')
    def closest(self, *args, **kwargs):
        """Closest method that preserves entity and business status.
        """
        return _pendulum.Date.closest(self, *args, **kwargs)

    @store_calendar(typ='Date')
    def farthest(self, *args, **kwargs):
        """Farthest method that preserves entity and business status.
        """
        return _pendulum.Date.farthest(self, *args, **kwargs)

    @store_calendar(typ='Date')
    def average(self, dt=None):
        """Modify the current instance to the average
        of a given instance (default now) and the current instance.

        Parameters
            dt: The date to average with (defaults to today)

        Returns
            A new Date object representing the average date
        """
        return _pendulum.Date.average(self, dt)

    @classmethod
    def fromordinal(cls, *args, **kwargs) -> Self:
        """Create a Date from an ordinal.

        Parameters
            n: The ordinal value

        Returns
            Date instance
        """
        result = _pendulum.Date.fromordinal(*args, **kwargs)
        return cls.instance(result)

    @classmethod
    def fromtimestamp(cls, timestamp, tz=None) -> Self:
        """Create a Date from a timestamp.

        Parameters
            timestamp: Unix timestamp
            tz: Optional timezone (defaults to UTC)

        Returns
            Date instance
        """
        # Ensure timezone is always applied to get consistent results
        tz = tz or UTC
        dt = _datetime.datetime.fromtimestamp(timestamp, tz=tz)
        return cls(dt.year, dt.month, dt.day)

    @store_calendar(typ='Date')
    def nth_of(self, unit: str, nth: int, day_of_week) -> Self:
        """Returns a new instance set to the given occurrence
        of a given day of the week in the current unit.

        Parameters
            unit: The unit to use ("month", "quarter", or "year")
            nth: The position of the day in the unit (1 to 5)
            day_of_week: The day of the week (pendulum.MONDAY to pendulum.SUNDAY)

        Returns
            A new Date object for the nth occurrence

        Raises
            ValueError: If the occurrence can't be found
        """
        return _pendulum.Date.nth_of(self, unit, nth, day_of_week)

    @classmethod
    def parse(
        cls,
        s: str | None,
        calendar: str | Calendar = 'NYSE',
        raise_err: bool = False,
    ) -> Self | None:
        """Convert a string to a date handling many different formats.

        Supports various date formats including:
        - Standard formats: YYYY-MM-DD, MM/DD/YYYY, MM/DD/YY, YYYYMMDD
        - Named months: DD-MON-YYYY, MON-DD-YYYY, Month DD, YYYY
        - Special codes: T (today), Y (yesterday), P (previous business day)
        - Business day offsets: T-3b, P+2b (add/subtract business days)

        Parameters
            s: String to parse or None
            calendar: Calendar name or instance for business day calculations (default 'NYSE')
            raise_err: If True, raises ValueError on parse failure instead of returning None

        Returns
            Date instance or None if parsing fails and raise_err is False

        Examples
            Standard numeric formats:
            Date.parse('2020-01-15') → Date(2020, 1, 15)
            Date.parse('01/15/2020') → Date(2020, 1, 15)
            Date.parse('01/15/20') → Date(2020, 1, 15)
            Date.parse('20200115') → Date(2020, 1, 15)

            Named month formats:
            Date.parse('15-Jan-2020') → Date(2020, 1, 15)
            Date.parse('Jan 15, 2020') → Date(2020, 1, 15)
            Date.parse('15JAN2020') → Date(2020, 1, 15)

            Special codes:
            Date.parse('T') → today's date
            Date.parse('Y') → yesterday's date
            Date.parse('P') → previous business day
            Date.parse('M') → last day of previous month

            Business day offsets:
            Date.parse('T-3b') → 3 business days ago
            Date.parse('P+2b') → 2 business days after previous business day
            Date.parse('T+5') → 5 calendar days from today
        """

        def date_for_symbol(s):
            if s == 'N':
                return cls.today()
            if s == 'T':
                return cls.today()
            if s == 'Y':
                return cls.today().subtract(days=1)
            if s == 'P':
                return cls.today().calendar(calendar).business().subtract(days=1)
            if s == 'M':
                return cls.today().start_of('month').subtract(days=1)

        if not s:
            if raise_err:
                raise ValueError('Empty value')
            return

        if not isinstance(s, str):
            raise TypeError(f'Invalid type for date parse: {s.__class__}')

        with contextlib.suppress(ValueError):
            if float(s) and len(s) != 8:  # 20000101
                if raise_err:
                    raise ValueError('Invalid date: %s', s)
                return

        # special shortcode symbolic values: T, Y-2, P-1b
        if m := DATEMATCH.match(s):
            d = date_for_symbol(m.groupdict().get('d'))
            n = m.groupdict().get('n')
            if not n:
                return d
            n = int(n)
            b = m.groupdict().get('b')
            if b:
                if b != 'b':
                    raise ValueError(f"Expected 'b' for business day modifier, got '{b}'")
                d = d.calendar(calendar).business().add(days=n)
            else:
                d = d.add(days=n)
            return d
        if 'today' in s.lower():
            return cls.today()
        if 'yester' in s.lower():
            return cls.today().subtract(days=1)

        parsed = _rust_parse_datetime(s)
        if parsed is not None:
            return cls.instance(parsed)

        if raise_err:
            raise ValueError('Failed to parse date: %s', s)

    @classmethod
    def instance(
        cls,
        obj: _datetime.date
        | _datetime.datetime
        | _datetime.time
        | pd.Timestamp
        | np.datetime64
        | Self
        | None,
        raise_err: bool = False,
    ) -> Self | None:
        """Create a Date instance from various date-like objects.

        Converts datetime.date, datetime.datetime, pandas Timestamp,
        numpy datetime64, and other date-like objects to Date instances.

        Parameters
            obj: Date-like object to convert
            raise_err: If True, raises ValueError for None/NA values instead of returning None

        Returns
            Date instance or None if obj is None/NA and raise_err is False
        """
        if pd.isna(obj):
            if raise_err:
                raise ValueError('Empty value')
            return

        if type(obj) is cls:
            return obj

        if isinstance(obj, pd.Timestamp):
            obj = obj.to_pydatetime()
            return cls(obj.year, obj.month, obj.day)

        if isinstance(obj, np.datetime64):
            obj = np.datetime64(obj, 'us').astype(_datetime.datetime)
            return cls(obj.year, obj.month, obj.day)

        return cls(obj.year, obj.month, obj.day)

    @classmethod
    def today(cls) -> Self:
        d = _datetime.datetime.now(LCL)
        return cls(d.year, d.month, d.day)

    def isoweek(self) -> int | None:
        """Get ISO week number (1-52/53) following ISO week-numbering standard.
        """
        with contextlib.suppress(Exception):
            return self.isocalendar()[1]

    def lookback(self, unit='last') -> Self:
        """Get date in the past based on lookback unit.

        Supported units: 'last'/'day' (1 day), 'week', 'month', 'quarter', 'year'.
        Respects business day mode if enabled.
        """
        def _lookback(years=0, months=0, weeks=0, days=0):
            _business = self._business
            self._business = False
            d = self\
                .subtract(years=years, months=months, weeks=weeks, days=days)
            if _business:
                return d._business_or_previous()
            return d

        return {
            'day': _lookback(days=1),
            'last': _lookback(days=1),
            'week': _lookback(weeks=1),
            'month': _lookback(months=1),
            'quarter': _lookback(months=3),
            'year': _lookback(years=1),
            }.get(unit)
