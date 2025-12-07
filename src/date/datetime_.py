from __future__ import annotations

import datetime as _datetime
import sys
import zoneinfo as _zoneinfo
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pendulum as _pendulum

from date.constants import LCL, UTC, Timezone
from date.decorators import store_calendar
from date.helpers import _rust_parse_datetime
from date.mixins import DateBusinessMixin

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from date.calendars import Calendar
    from date.date_ import Date
    from date.time_ import Time


class DateTime(DateBusinessMixin, _pendulum.DateTime):
    """DateTime class extending pendulum.DateTime with business day and additional functionality.

    This class inherits all pendulum.DateTime functionality while adding:
    - Business day calculations with NYSE calendar integration
    - Enhanced timezone handling
    - Extended parsing capabilities
    - Custom utility methods for financial applications

    Unlike pendulum.DateTime:
    - today() returns start of day rather than current time
    - Methods preserve business status and entity when chaining
    - Has timezone handling helpers not present in pendulum
    """

    def epoch(self) -> float:
        """Translate a datetime object into unix seconds since epoch
        """
        return self.timestamp()

    @store_calendar(typ='DateTime')
    def astimezone(self, *args, **kwargs):
        """Convert to a timezone-aware datetime in a different timezone.
        """
        return _pendulum.DateTime.astimezone(self, *args, **kwargs)

    @store_calendar(typ='DateTime')
    def in_timezone(self, *args, **kwargs):
        """Convert to a timezone-aware datetime in a different timezone.
        """
        return _pendulum.DateTime.in_timezone(self, *args, **kwargs)

    @store_calendar(typ='DateTime')
    def in_tz(self, *args, **kwargs):
        """Convert to a timezone-aware datetime in a different timezone.
        """
        return _pendulum.DateTime.in_tz(self, *args, **kwargs)

    @store_calendar(typ='DateTime')
    def replace(self, *args, **kwargs):
        """Replace method that preserves entity and business status.
        """
        return _pendulum.DateTime.replace(self, *args, **kwargs)

    @classmethod
    def fromordinal(cls, *args, **kwargs) -> Self:
        """Create a DateTime from an ordinal.

        Parameters
            n: The ordinal value

        Returns
            DateTime instance
        """
        result = _pendulum.DateTime.fromordinal(*args, **kwargs)
        return cls.instance(result)

    @classmethod
    def fromtimestamp(cls, timestamp, tz=None) -> Self:
        """Create a DateTime from a timestamp.

        Parameters
            timestamp: Unix timestamp
            tz: Optional timezone

        Returns
            DateTime instance
        """
        tz = tz or UTC
        result = _pendulum.DateTime.fromtimestamp(timestamp, tz)
        return cls.instance(result)

    @classmethod
    def strptime(cls, time_str, fmt) -> Self:
        """Parse a string into a DateTime according to a format.

        Parameters
            time_str: String to parse
            fmt: Format string

        Returns
            DateTime instance
        """
        result = _pendulum.DateTime.strptime(time_str, fmt)
        return cls.instance(result)

    @classmethod
    def utcfromtimestamp(cls, timestamp) -> Self:
        """Create a UTC DateTime from a timestamp.

        Parameters
            timestamp: Unix timestamp

        Returns
            DateTime instance
        """
        result = _pendulum.DateTime.utcfromtimestamp(timestamp)
        return cls.instance(result)

    @classmethod
    def utcnow(cls) -> Self:
        """Create a DateTime representing current UTC time.

        Returns
            DateTime instance
        """
        result = _pendulum.DateTime.utcnow()
        return cls.instance(result)

    @classmethod
    def now(cls, tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = None) -> Self:
        """Get a DateTime instance for the current date and time.
        """
        if tz is None or tz == 'local':
            d = _datetime.datetime.now(LCL)
        elif tz is UTC or tz == 'UTC':
            d = _datetime.datetime.now(UTC)
        else:
            d = _datetime.datetime.now(UTC)
            tz = _pendulum._safe_timezone(tz)
            d = d.astimezone(tz)
        return cls(d.year, d.month, d.day, d.hour, d.minute, d.second,
                   d.microsecond, tzinfo=d.tzinfo, fold=d.fold)

    @classmethod
    def today(cls, tz: str | _zoneinfo.ZoneInfo | None = None) -> Self:
        """Create a DateTime object representing today at the start of day.

        Unlike pendulum.today() which returns current time, this method
        returns a DateTime object at 00:00:00 of the current day.

        Parameters
            tz: Optional timezone (defaults to local timezone)

        Returns
            DateTime instance representing start of current day
        """
        return DateTime.now(tz).start_of('day')

    def date(self) -> Date:
        from date.date_ import Date
        return Date(self.year, self.month, self.day)

    @classmethod
    def combine(
        cls,
        date: _datetime.date,
        time: _datetime.time,
        tzinfo: _zoneinfo.ZoneInfo | None = None,
    ) -> Self:
        """Combine date and time (*behaves differently from Pendulum `combine`*).
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
        from date.time_ import Time
        return Time.instance(self)

    @classmethod
    def parse(
        cls, s: str | int | None,
        calendar: str | Calendar = 'NYSE',
        raise_err: bool = False
        ) -> Self | None:
        """Convert a string or timestamp to a DateTime with extended format support.

        Unlike pendulum's parse, this method supports:
        - Unix timestamps (int/float, handles milliseconds automatically)
        - Special codes: T (today), Y (yesterday), P (previous business day)
        - Business day offsets: T-3b, P+2b (add/subtract business days)
        - Multiple date-time formats beyond ISO 8601
        - Combined date and time strings with various separators

        Parameters
            s: String or timestamp to parse
            calendar: Calendar name or instance for business day calculations (default 'NYSE')
            raise_err: If True, raises ValueError on parse failure instead of returning None

        Returns
            DateTime instance or None if parsing fails and raise_err is False

        Examples
            Unix timestamps:
            DateTime.parse(1609459200) → DateTime(2021, 1, 1, 0, 0, 0, tzinfo=LCL)
            DateTime.parse(1609459200000) → DateTime(2021, 1, 1, 0, 0, 0, tzinfo=LCL)

            ISO 8601 format:
            DateTime.parse('2020-01-15T14:30:00') → DateTime(2020, 1, 15, 14, 30, 0)

            Date and time separated:
            DateTime.parse('2020-01-15 14:30:00') → DateTime(2020, 1, 15, 14, 30, 0, tzinfo=LCL)
            DateTime.parse('01/15/2020:14:30:00') → DateTime(2020, 1, 15, 14, 30, 0, tzinfo=LCL)

            Date only (time defaults to 00:00:00):
            DateTime.parse('2020-01-15') → DateTime(2020, 1, 15, 0, 0, 0)
            DateTime.parse('01/15/2020') → DateTime(2020, 1, 15, 0, 0, 0)

            Time only (uses today's date):
            DateTime.parse('14:30:00') → DateTime(today's year, month, day, 14, 30, 0, tzinfo=LCL)

            Special codes:
            DateTime.parse('T') → today at 00:00:00
            DateTime.parse('Y') → yesterday at 00:00:00
            DateTime.parse('P') → previous business day at 00:00:00
        """
        from date.date_ import Date
        from date.time_ import Time

        if not s:
            if raise_err:
                raise ValueError('Empty value')
            return

        if not isinstance(s, (str, int, float)):
            raise TypeError(f'Invalid type for datetime parse: {s.__class__}')

        if isinstance(s, (int, float)):
            if len(str(int(s))) == 13:
                s /= 1000  # Convert from milliseconds to seconds
            dt = _datetime.datetime.fromtimestamp(s)
            return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                       dt.second, dt.microsecond, tzinfo=LCL)

        parsed = _rust_parse_datetime(s)
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
        """Create a DateTime instance from various datetime-like objects.

        Provides unified interface for converting different date/time types
        including pandas and numpy datetime objects into DateTime instances.

        Unlike pendulum, this method:
        - Handles pandas Timestamp and numpy datetime64 objects
        - Adds timezone (UTC by default) when none is specified
        - Has special handling for Time objects (combines with current date)

        Parameters
            obj: Date, datetime, time, or compatible object to convert
            tz: Optional timezone to apply (if None, uses obj's timezone or UTC)
            raise_err: If True, raises ValueError for None/NA values instead of returning None

        Returns
            DateTime instance or None if obj is None/NA and raise_err is False
        """
        from date.date_ import Date
        from date.time_ import Time

        if pd.isna(obj):
            if raise_err:
                raise ValueError('Empty value')
            return

        if type(obj) is cls and not tz:
            return obj

        if isinstance(obj, pd.Timestamp):
            obj = obj.to_pydatetime()
            tz = tz or obj.tzinfo or UTC
            if tz is _datetime.timezone.utc:
                tz = UTC
            elif hasattr(tz, 'zone'):
                tz = Timezone(tz.zone)
            elif isinstance(tz, str):
                tz = Timezone(tz)
            return cls(obj.year, obj.month, obj.day, obj.hour, obj.minute,
                       obj.second, obj.microsecond, tzinfo=tz)

        if isinstance(obj, np.datetime64):
            obj = np.datetime64(obj, 'us').astype(_datetime.datetime)
            tz = tz or UTC
            return cls(obj.year, obj.month, obj.day, obj.hour, obj.minute,
                       obj.second, obj.microsecond, tzinfo=tz)

        if type(obj) is Date:
            return cls(obj.year, obj.month, obj.day, tzinfo=tz or UTC)

        if isinstance(obj, _datetime.date) and not isinstance(obj, _datetime.datetime):
            return cls(obj.year, obj.month, obj.day, tzinfo=tz or UTC)

        tz = tz or obj.tzinfo or UTC

        if type(obj) is Time:
            return cls.combine(Date.today(), obj, tzinfo=tz)

        if isinstance(obj, _datetime.time):
            from date.date_ import Date
            return cls.combine(Date.today(), obj, tzinfo=tz)

        return cls(obj.year, obj.month, obj.day, obj.hour, obj.minute,
                   obj.second, obj.microsecond, tzinfo=tz)
