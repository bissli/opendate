from __future__ import annotations

import datetime as _datetime
import sys
import zoneinfo as _zoneinfo
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import pendulum as _pendulum
from opendate.constants import DATEMATCH, LCL, PENDULUM_TIMEZONES, UTC
from opendate.constants import normalize_timezone
from opendate.date_ import Date
from opendate.helpers import _rust_parse_datetime
from opendate.metaclass import DATETIME_METHODS_RETURNING_DATETIME
from opendate.metaclass import DateContextMeta
from opendate.mixins import DateBusinessMixin
from opendate.time_ import Time

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from opendate.calendars import Calendar


class DateTime(
    DateBusinessMixin,
    _pendulum.DateTime,
    metaclass=DateContextMeta,
    methods_to_wrap=DATETIME_METHODS_RETURNING_DATETIME
):
    """pendulum.DateTime with business-day arithmetic and extended parsing.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Build the instance, rebuilding a tzinfo pendulum cannot read.

        Parameters
        ----------
        *args : Any
            The datetime.datetime fields in order, tzinfo eighth. A str
            tzinfo, here or by keyword, is read as a zone name, which the
            stdlib rejects.
        **kwargs : Any
            The same fields by keyword, plus fold.

        Returns
        -------
        DateTime
            The new instance, carrying a pendulum timezone wherever the
            caller supplied any timezone at all. Unpickling rebuilds the
            timezone too, so a value pickled with a tzinfo pendulum
            cannot read loads with a pendulum one.

        See Also
        --------
        opendate.constants.normalize_timezone : the rebuild itself
        """
        if len(args) > 7:
            tzinfo = args[7]
        elif kwargs:
            tzinfo = kwargs.get('tzinfo')
        else:
            return super().__new__(cls, *args)
        if tzinfo is None or isinstance(tzinfo, PENDULUM_TIMEZONES):
            return super().__new__(cls, *args, **kwargs)

        if args and isinstance(args[0], bytes):
            # The pickle byte-state form carries no date to read a zone
            # at, and the stdlib ignores a tzinfo keyword beside it.
            return super().__new__(cls, *args, **kwargs)

        if isinstance(tzinfo, str):
            # A str is not a tzinfo, so it cannot go into the reference
            # built below.
            settled = normalize_timezone(tzinfo)
            if 'tzinfo' in kwargs:
                kwargs['tzinfo'] = settled
            else:
                args = (*args[:7], settled, *args[8:])
            return super().__new__(cls, *args, **kwargs)

        # Notes:
        # - The reference carries tzinfo and the caller's fold, since a
        #   tzinfo may read either to pick a side of an ambiguous hour.
        # - Date parts default to 1, since 0 raises here before
        #   super().__new__ can report the missing argument.
        fields = ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond')
        parts = list(args[:7])
        parts += [
            kwargs.get(field, 1 if index < 3 else 0)
            for index, field in enumerate(fields) if index >= len(parts)
            ]
        when = _datetime.datetime(*parts, tzinfo=tzinfo, fold=kwargs.get('fold', 0))
        settled = normalize_timezone(tzinfo, when)

        if 'tzinfo' in kwargs:
            kwargs['tzinfo'] = settled
        else:
            args = (*args[:7], settled, *args[8:])
        return super().__new__(cls, *args, **kwargs)

    def epoch(self) -> float:
        """Translate a datetime object into unix seconds since epoch
        """
        return self.timestamp()

    @classmethod
    def fromordinal(cls, *args: int, **kwargs: Any) -> Self:
        """Midnight UTC on a proleptic Gregorian ordinal day.

        Parameters
        ----------
        *args : int
            The ordinal, where 1 is January 1 of year 1.
        **kwargs : Any
            Passed to pendulum.DateTime.fromordinal.

        Returns
        -------
        DateTime
        """
        result = _pendulum.DateTime.fromordinal(*args, **kwargs)
        return cls.instance(result)

    @classmethod
    def fromtimestamp(
        cls,
        timestamp: float,
        tz: str | _datetime.tzinfo | None = None
        ) -> Self:
        """The instant of a Unix timestamp, read in tz.

        Parameters
        ----------
        timestamp : float
            Seconds since the Unix epoch.
        tz : str | tzinfo | None, default None
            Zone of the result. None gives UTC.

        Returns
        -------
        DateTime
        """
        tz = tz or UTC
        result = _pendulum.DateTime.fromtimestamp(timestamp, tz)
        return cls.instance(result)

    @classmethod
    def strptime(cls, time_str: str, fmt: str) -> Self:
        """Parse time_str by the strptime format fmt.

        Parameters
        ----------
        time_str : str
            Text to parse.
        fmt : str
            strptime format.

        Returns
        -------
        DateTime
            UTC where fmt reads no offset.
        """
        result = _pendulum.DateTime.strptime(time_str, fmt)
        return cls.instance(result)

    @classmethod
    def utcfromtimestamp(cls, timestamp: float) -> Self:
        """The instant of a Unix timestamp, in UTC.

        Parameters
        ----------
        timestamp : float
            Seconds since the Unix epoch.

        Returns
        -------
        DateTime
        """
        result = _pendulum.DateTime.utcfromtimestamp(timestamp)
        return cls.instance(result)

    @classmethod
    def utcnow(cls) -> Self:
        """Current date and time in UTC.
        """
        result = _pendulum.DateTime.utcnow()
        return cls.instance(result)

    @classmethod
    def now(cls, tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = None) -> Self:
        """Current date and time in tz.

        Parameters
        ----------
        tz : str | ZoneInfo | tzinfo | None, default None
            None or 'local' gives the local zone LCL, where `instance`
            would default to UTC.

        Returns
        -------
        DateTime
        """
        if tz is None or tz == 'local':
            d = _datetime.datetime.now(LCL)
        elif tz is UTC or tz == 'UTC':
            d = _datetime.datetime.now(UTC)
        else:
            d = _datetime.datetime.now(UTC)
            tz = _pendulum._safe_timezone(tz)
            d = d.astimezone(tz)
        return cls(
            d.year,
            d.month,
            d.day,
            d.hour,
            d.minute,
            d.second,
            d.microsecond,
            tzinfo=d.tzinfo,
            fold=d.fold)

    @classmethod
    def today(cls, tz: str | _zoneinfo.ZoneInfo | None = None) -> Self:
        """Start of the current day in tz.

        Parameters
        ----------
        tz : str | ZoneInfo | None, default None
            None gives the local zone LCL.

        Returns
        -------
        DateTime
            00:00:00 today, where pendulum.today() gives the current time.
        """
        return DateTime.now(tz).start_of('day')

    def date(self) -> Date:
        """Wall-clock calendar date, as a Date.
        """
        return Date(self.year, self.month, self.day)

    @classmethod
    def combine(
        cls,
        date: _datetime.date,
        time: _datetime.time,
        tzinfo: _zoneinfo.ZoneInfo | None = None,
    ) -> Self:
        """DateTime from a date and a time, in tzinfo or the time's own zone.

        Parameters
        ----------
        date : datetime.date
            Calendar day.
        time : datetime.time
            Wall-clock time.
        tzinfo : ZoneInfo | None, default None
            Zone set on the wall-clock result, with no conversion. None
            takes the time's own zone, then UTC.

        Returns
        -------
        DateTime
        """
        _tzinfo = tzinfo or time.tzinfo
        return DateTime.instance(_datetime.datetime.combine(date, time, tzinfo=_tzinfo))

    def rfc3339(self) -> str:
        """Return RFC 3339 formatted string (same as isoformat()).
        """
        return self.isoformat()

    def time(self) -> Time:
        """Extract time component from datetime (preserving timezone).
        """
        return Time.instance(self)

    @classmethod
    def parse(
        cls, s: str | int | None,
        calendar: str | Calendar = 'NYSE',
        raise_err: bool = False
        ) -> Self | None:
        """DateTime from a string, a date code or a Unix timestamp.

        Parameters
        ----------
        s : str | int | None
            A date-time, date or time string, a date code, or a Unix
            timestamp. A 13-digit number is read as milliseconds. A date
            code is T (today), Y (yesterday) or P (previous business day),
            with an optional offset such as T-3 or P+2b, where b counts
            business days.
        calendar : str | Calendar, default 'NYSE'
            Calendar for business-day codes and offsets.
        raise_err : bool, default False
            Raise ValueError on an empty or unreadable s instead of
            returning None.

        Returns
        -------
        DateTime | None
            A timestamp gives its local wall time in LCL. A date code gives
            a naive midnight. A bare time takes today's date. None where s
            is empty or unreadable and raise_err is False.

        Raises
        ------
        TypeError
            s is not a str, int or float.
        ValueError
            s is empty or unreadable and raise_err is True.

        Examples
        --------
        DateTime.parse('2020-01-15T14:30:00') -> 2020-01-15 14:30:00 UTC
        DateTime.parse('01/15/2020:14:30:00') -> 2020-01-15 14:30:00 UTC
        DateTime.parse('01/15/2020') -> 2020-01-15 00:00:00 UTC
        DateTime.parse('14:30:00') -> today at 14:30:00 UTC
        DateTime.parse('P') -> previous business day at 00:00:00, naive
        """
        if not s:
            if raise_err:
                raise ValueError('Empty value')
            return

        if not isinstance(s, (str, int, float)):
            raise TypeError(f'Invalid type for datetime parse: {s.__class__}')

        if isinstance(s, (int, float)):
            if len(str(int(s))) == 13:
                s /= 1000
            dt = _datetime.datetime.fromtimestamp(s)
            return cls(
                dt.year,
                dt.month,
                dt.day,
                dt.hour,
                dt.minute,
                dt.second,
                dt.microsecond,
                tzinfo=LCL)

        parsed = None if DATEMATCH.match(s) else _rust_parse_datetime(s)
        if parsed is not None:
            return cls.instance(parsed)

        for delim in (' ', ':'):
            bits = s.split(delim, 1)
            if len(bits) == 2:
                d = Date.parse(bits[0])
                t = Time.parse(bits[1])
                if d is not None and t is not None:
                    return DateTime.combine(d, t, LCL)

        d = Date.parse(s, calendar=calendar)
        if d is not None:
            return cls(d.year, d.month, d.day, 0, 0, 0)

        current = Date.today()
        t = Time.parse(s)
        if t is not None:
            return cls.combine(current, t, LCL)

        if raise_err:
            raise ValueError('Invalid date-time format: %s', s)

    @classmethod
    def instance(
        cls,
        obj: _datetime.date
        | _datetime.time
        | pd.Timestamp
        | np.datetime64
        | Self
        | None,
        tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = None,
        raise_err: bool = False,
    ) -> Self | None:
        """DateTime from a date, datetime, time, pandas or numpy value.

        Parameters
        ----------
        obj : date | time | pd.Timestamp | np.datetime64 | DateTime | None
            A date gives midnight. A time takes today's date. A DateTime
            comes back as the same object where tz is None.
        tz : str | ZoneInfo | tzinfo | None, default None
            Zone set on obj's wall-clock value, with no conversion. None
            keeps obj's own zone, or gives UTC where obj has none.
        raise_err : bool, default False
            Raise ValueError on a None or NA obj instead of returning None.

        Returns
        -------
        DateTime | None
            None where obj is None or NA and raise_err is False.

        Raises
        ------
        ValueError
            obj is None or NA and raise_err is True.
        """
        if pd.isna(obj):
            if raise_err:
                raise ValueError('Empty value')
            return

        if type(obj) is cls and not tz:
            return obj

        if isinstance(obj, pd.Timestamp):
            obj = obj.to_pydatetime()

        if isinstance(obj, np.datetime64):
            obj = np.datetime64(obj, 'us').astype(_datetime.datetime)

        if type(obj) is Date:
            return cls(obj.year, obj.month, obj.day, tzinfo=tz or UTC)

        if isinstance(obj, _datetime.date) and not isinstance(obj, _datetime.datetime):
            return cls(obj.year, obj.month, obj.day, tzinfo=tz or UTC)

        tz = tz or obj.tzinfo or UTC

        if type(obj) is Time:
            return cls.combine(Date.today(), obj, tzinfo=tz)

        if isinstance(obj, _datetime.time):
            return cls.combine(Date.today(), obj, tzinfo=tz)

        return cls(
            obj.year,
            obj.month,
            obj.day,
            obj.hour,
            obj.minute,
            obj.second,
            obj.microsecond,
            tzinfo=tz)
