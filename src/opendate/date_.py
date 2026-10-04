from __future__ import annotations

import contextlib
import datetime as _datetime
import sys
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pendulum as _pendulum
from opendate.constants import _IS_WINDOWS, DATEMATCH, LCL, UTC
from opendate.helpers import _rust_parse_datetime
from opendate.metaclass import DATE_METHODS_RETURNING_DATE, DateContextMeta
from opendate.mixins import DateBusinessMixin, DateExtrasMixin

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from opendate.calendars import Calendar


class Date(
    DateExtrasMixin,
    DateBusinessMixin,
    _pendulum.Date,
    metaclass=DateContextMeta,
    methods_to_wrap=DATE_METHODS_RETURNING_DATE
):
    """pendulum.Date with business-day arithmetic and extra date utilities.

    Unlike pendulum.Date, methods that create new instances return Date objects
    that preserve business status and entity association when chained.
    """

    def to_string(self, fmt: str) -> str:
        """Format date to string, handling platform-specific format codes.

        Parameters
        ----------
        fmt : str
            strftime format. On Windows each '%-' becomes '%#', so '%-d'
            drops the leading zero on every platform.

        Returns
        -------
        str
            The formatted date.
        """
        return self.strftime(fmt.replace('%-', '%#') if _IS_WINDOWS else fmt)

    @classmethod
    def fromordinal(cls, *args: int, **kwargs: int) -> Self:
        """Create a Date from an ordinal.

        Parameters
        ----------
        *args : int
            The proleptic Gregorian ordinal, 1 being 0001-01-01.
        **kwargs : int
            Any keyword raises TypeError: the ordinal is positional only.

        Returns
        -------
        Date
        """
        result = _pendulum.Date.fromordinal(*args, **kwargs)
        return cls.instance(result)

    @classmethod
    def fromtimestamp(
        cls,
        timestamp: float,
        tz: _datetime.tzinfo | None = None,
    ) -> Self:
        """Create a Date from a timestamp.

        Parameters
        ----------
        timestamp : float
            Seconds since the Unix epoch.
        tz : datetime.tzinfo or None, default None
            Zone whose calendar dates the instant. None means UTC.

        Returns
        -------
        Date
        """
        tz = tz or UTC
        dt = _datetime.datetime.fromtimestamp(timestamp, tz=tz)
        return cls(dt.year, dt.month, dt.day)

    @classmethod
    def parse(
        cls,
        s: str | None,
        calendar: str | Calendar = 'NYSE',
        raise_err: bool = False,
    ) -> Self | None:
        """Convert a string to a date handling many different formats.

        Parameters
        ----------
        s : str or None
            Text to parse: a numeric date (YYYY-MM-DD, MM/DD/YYYY,
            MM/DD/YY, YYYYMMDD), a named-month date (DD-MON-YYYY,
            MON-DD-YYYY, Month DD, YYYY), or a code - T (today),
            Y (yesterday), P (previous business day) - with an optional
            day offset, where a trailing b counts business days (T-3b).
            Any other all-numeric string is unparseable.
        calendar : str or Calendar, default 'NYSE'
            Calendar name or instance for the P code and business-day
            offsets.
        raise_err : bool, default False
            Raise ValueError on empty or unparseable input instead of
            returning None.

        Returns
        -------
        Date or None
            None for empty or unparseable input when raise_err is False.

        Raises
        ------
        TypeError
            s is neither empty nor a str.
        ValueError
            raise_err is True and s is empty or unparseable.

        Examples
        --------
        Standard numeric formats:
        Date.parse('2020-01-15') -> Date(2020, 1, 15)
        Date.parse('01/15/2020') -> Date(2020, 1, 15)
        Date.parse('01/15/20') -> Date(2020, 1, 15)
        Date.parse('20200115') -> Date(2020, 1, 15)

        Named month formats:
        Date.parse('15-Jan-2020') -> Date(2020, 1, 15)
        Date.parse('Jan 15, 2020') -> Date(2020, 1, 15)
        Date.parse('15JAN2020') -> Date(2020, 1, 15)

        Special codes:
        Date.parse('T') -> today's date
        Date.parse('Y') -> yesterday's date
        Date.parse('P') -> previous business day
        Date.parse('M') -> last day of previous month

        Business day offsets:
        Date.parse('T-3b') -> 3 business days ago
        Date.parse('P+2b') -> 2 business days after previous business day
        Date.parse('T+5') -> 5 calendar days from today
        """

        def date_for_symbol(s: str) -> Self | None:
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

        bad_number = False
        with contextlib.suppress(ValueError):
            bad_number = bool(float(s)) and len(s) != 8
        if bad_number:
            if raise_err:
                raise ValueError(f'Invalid date: {s}')
            return

        if m := DATEMATCH.match(s):
            d = date_for_symbol(m.groupdict().get('d'))
            n = m.groupdict().get('n')
            if not n:
                return d
            n = int(n)
            if m.groupdict().get('b'):
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
            raise ValueError(f'Failed to parse date: {s}')

    @classmethod
    def instance(
        cls,
        obj: _datetime.date
        | _datetime.datetime
        | pd.Timestamp
        | np.datetime64
        | Self
        | None,
        raise_err: bool = False,
    ) -> Self | None:
        """Create a Date instance from various date-like objects.

        Parameters
        ----------
        obj : date, datetime, pd.Timestamp, np.datetime64, Date or None
            Date-like object to convert.
        raise_err : bool, default False
            Raise ValueError for None or NA instead of returning None.

        Returns
        -------
        Date or None
            obj itself when it is already this class. None for None or NA
            when raise_err is False.

        Raises
        ------
        ValueError
            raise_err is True and obj is None or NA.
        """
        if pd.isna(obj):
            if raise_err:
                raise ValueError('Empty value')
            return

        if type(obj) is cls:
            return obj

        if isinstance(obj, pd.Timestamp):
            obj = obj.to_pydatetime()
        elif isinstance(obj, np.datetime64):
            obj = np.datetime64(obj, 'us').astype(_datetime.datetime)

        return cls(obj.year, obj.month, obj.day)

    @classmethod
    def today(cls) -> Self:
        """Today's date in the local zone, LCL.
        """
        d = _datetime.datetime.now(LCL)
        return cls(d.year, d.month, d.day)

    def isoweek(self) -> int | None:
        """Get ISO week number (1-52/53) following ISO week-numbering standard.
        """
        with contextlib.suppress(Exception):
            return self.isocalendar()[1]

    def lookback(self, unit: str = 'last') -> Self | None:
        """Get date in the past based on lookback unit.

        Parameters
        ----------
        unit : str, default 'last'
            'last' or 'day' (1 day), 'week', 'month', 'quarter' (3 months)
            or 'year'.

        Returns
        -------
        Date or None
            None for any other unit. In business mode a result that is
            not a business day rolls back to the previous one.
        """
        _units = {
            'day': {'days': 1},
            'last': {'days': 1},
            'week': {'weeks': 1},
            'month': {'months': 1},
            'quarter': {'months': 3},
            'year': {'years': 1},
            }
        kwargs = _units.get(unit)
        if kwargs is None:
            return None
        _business = self._business
        self._business = False
        d = self.subtract(**kwargs)
        if _business:
            return d._business_or_previous()
        return d
