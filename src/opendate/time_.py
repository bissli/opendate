from __future__ import annotations

import datetime as _datetime
import sys
import time
import zoneinfo as _zoneinfo

import numpy as np
import pandas as pd
import pendulum as _pendulum

from opendate.constants import UTC
from opendate.decorators import prefer_utc_timezone
from opendate.helpers import _rust_parse_time

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class Time(_pendulum.Time):
    """Time class extending pendulum.Time with additional functionality.

    This class inherits all pendulum.Time functionality while adding:
    - Enhanced parsing for various time formats
    - Default UTC timezone when created
    - Simple timezone conversion utilities

    Unlike pendulum.Time, this class has more lenient parsing capabilities
    and different timezone defaults.
    """

    @classmethod
    @prefer_utc_timezone
    def parse(cls, s: str | None, fmt: str | None = None, raise_err: bool = False) -> Self | None:
        """Parse time string in various formats.

        Supported formats:
        - hh:mm or hh.mm
        - hh:mm:ss or hh.mm.ss
        - hh:mm:ss.microseconds
        - Any of above with AM/PM
        - Compact: hhmmss or hhmmss.microseconds

        Returns Time with UTC timezone by default.

        Parameters
            s: String to parse or None
            fmt: Optional strftime format string for custom parsing
            raise_err: If True, raises ValueError on parse failure instead of returning None

        Returns
            Time instance with UTC timezone or None if parsing fails and raise_err is False

        Examples
            Basic time formats:
            Time.parse('14:30') → Time(14, 30, 0, 0, tzinfo=UTC)
            Time.parse('14.30') → Time(14, 30, 0, 0, tzinfo=UTC)
            Time.parse('14:30:45') → Time(14, 30, 45, 0, tzinfo=UTC)

            With microseconds:
            Time.parse('14:30:45.123456') → Time(14, 30, 45, 123456000, tzinfo=UTC)
            Time.parse('14:30:45,500000') → Time(14, 30, 45, 500000000, tzinfo=UTC)

            AM/PM formats:
            Time.parse('2:30 PM') → Time(14, 30, 0, 0, tzinfo=UTC)
            Time.parse('11:30 AM') → Time(11, 30, 0, 0, tzinfo=UTC)
            Time.parse('12:30 PM') → Time(12, 30, 0, 0, tzinfo=UTC)

            Compact formats:
            Time.parse('143045') → Time(14, 30, 45, 0, tzinfo=UTC)
            Time.parse('1430') → Time(14, 30, 0, 0, tzinfo=UTC)

            Custom format:
            Time.parse('14-30-45', fmt='%H-%M-%S') → Time(14, 30, 45, 0, tzinfo=UTC)
        """
        if not s:
            if raise_err:
                raise ValueError('Empty value')
            return

        if not isinstance(s, str):
            raise TypeError(f'Invalid type for time parse: {s.__class__}')

        if fmt:
            try:
                return cls(*time.strptime(s, fmt)[3:6])
            except (ValueError, TypeError):
                if raise_err:
                    raise ValueError(f'Unable to parse {s} using fmt {fmt}')
                return

        result = _rust_parse_time(s)
        if result is not None:
            hour, minute, second, microsecond = result
            return cls(hour, minute, second, microsecond)

        if raise_err:
            raise ValueError('Failed to parse time: %s', s)

    @classmethod
    def instance(
        cls,
        obj: _datetime.time
        | _datetime.datetime
        | pd.Timestamp
        | np.datetime64
        | Self
        | None,
        tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = None,
        raise_err: bool = False,
    ) -> Self | None:
        """Create Time instance from time-like object.

        Adds UTC timezone by default unless obj is already a Time instance.
        """
        if pd.isna(obj):
            if raise_err:
                raise ValueError('Empty value')
            return

        if type(obj) is cls and not tz:
            return obj

        tz = tz or obj.tzinfo or UTC

        return cls(obj.hour, obj.minute, obj.second, obj.microsecond, tzinfo=tz)

    def in_timezone(self, tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo) -> Self:
        """Convert time to a different timezone.
        """
        from opendate.date_ import Date
        from opendate.datetime_ import DateTime

        _dt = DateTime.combine(Date.today(), self, tzinfo=self.tzinfo or UTC)
        return _dt.in_timezone(tz).time()

    in_tz = in_timezone
