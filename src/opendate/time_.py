from __future__ import annotations

import datetime as _datetime
import sys
import time
import zoneinfo as _zoneinfo
from typing import Any

import numpy as np
import pandas as pd
import pendulum as _pendulum

from opendate.constants import PENDULUM_TIMEZONES, TIMEOFFSET, UTC
from opendate.constants import normalize_timezone
from opendate.date_ import Date
from opendate.decorators import prefer_utc_timezone
from opendate.helpers import _rust_parse_time

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class Time(_pendulum.Time):
    """pendulum.Time with lenient string parsing.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Build the instance, rebuilding a tzinfo pendulum cannot read.

        Parameters
        ----------
        *args : Any
            The datetime.time fields in order, tzinfo fifth. A str tzinfo,
            here or by keyword, is read as a zone name, which the stdlib
            rejects.
        **kwargs : Any
            The same fields by keyword, plus fold.

        Returns
        -------
        Time
            The new instance, carrying a pendulum timezone wherever the
            caller supplied any timezone at all. A named zone answers None
            from utcoffset(), as a time has no date to read it at, so
            comparing such a time with an aware one raises TypeError.

        See Also
        --------
        opendate.constants.normalize_timezone : the rebuild itself
        """
        if len(args) > 4:
            tzinfo = args[4]
        elif kwargs:
            tzinfo = kwargs.get('tzinfo')
        else:
            return super().__new__(cls, *args)
        if tzinfo is None or isinstance(tzinfo, PENDULUM_TIMEZONES):
            return super().__new__(cls, *args, **kwargs)

        settled = normalize_timezone(tzinfo)
        if 'tzinfo' in kwargs:
            kwargs['tzinfo'] = settled
        else:
            args = (*args[:4], settled, *args[5:])
        return super().__new__(cls, *args, **kwargs)

    @classmethod
    @prefer_utc_timezone
    def parse(
        cls,
        s: str | None,
        fmt: str | None = None,
        raise_err: bool = False
        ) -> Self | None:
        """Time from a string, keeping any offset the string spells out.

        Parameters
        ----------
        s : str | None
            hh:mm, hh.mm, hh:mm:ss or hh.mm.ss, or compact hhmm or hhmmss.
            Seconds may carry a fraction after '.' or ','. A string may end
            in AM/PM, or else in Z or a signed hh:mm or hhmm offset.
        fmt : str | None, default None
            strptime format, used in place of the formats above. Only its
            hour, minute and second reach the result.
        raise_err : bool, default False
            Raise ValueError on an empty or unreadable s instead of
            returning None.

        Returns
        -------
        Time | None
            UTC where s spells no offset. None where s is empty or
            unreadable and raise_err is False.

        Raises
        ------
        TypeError
            s is not a str.
        ValueError
            s is empty or unreadable and raise_err is True.

        Examples
        --------
        Time.parse('14:30') -> Time(14, 30, 0, tzinfo=UTC)
        Time.parse('14:30:45.123456') -> Time(14, 30, 45, 123456, tzinfo=UTC)
        Time.parse('2:30 PM') -> Time(14, 30, 0, tzinfo=UTC)
        Time.parse('143045') -> Time(14, 30, 45, tzinfo=UTC)
        Time.parse('14-30-45', fmt='%H-%M-%S') -> Time(14, 30, 45, tzinfo=UTC)
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

        tzinfo = None
        if match := TIMEOFFSET.match(s):
            s, offset = match.group('time'), match.group('offset')
            tzinfo = UTC if offset == 'Z' else _datetime.timezone(
                (-1 if offset[0] == '-' else 1) * _datetime.timedelta(
                    hours=int(offset[1:3]), minutes=int(offset[-2:])))

        result = _rust_parse_time(s)
        if result is not None:
            hour, minute, second, microsecond = result
            return cls(hour, minute, second, microsecond, tzinfo=tzinfo)

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
        """Time from the time of day of a time-like value.

        Parameters
        ----------
        obj : time | datetime | pd.Timestamp | np.datetime64 | Time | None
            Value to read. A Time comes back as the same object where tz
            is None, naive or not.
        tz : str | ZoneInfo | tzinfo | None, default None
            Zone set on the wall-clock time, with no conversion. None
            keeps obj's own zone, or gives UTC where obj has none.
        raise_err : bool, default False
            Raise ValueError on a None or NA obj instead of returning None.

        Returns
        -------
        Time | None
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

        tz = tz or obj.tzinfo or UTC

        return cls(obj.hour, obj.minute, obj.second, obj.microsecond, tzinfo=tz)

    def in_timezone(self, tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo) -> Self:
        """The same instant as a time of day in tz.

        Parameters
        ----------
        tz : str | ZoneInfo | tzinfo
            Target zone.

        Returns
        -------
        Time
            Converted on today's date, so a daylight-saving zone answers
            by today's offset. A naive time is read as UTC.
        """
        # Circular import: opendate.datetime_ imports this module.
        from opendate.datetime_ import DateTime

        _dt = DateTime.combine(Date.today(), self, tzinfo=self.tzinfo or UTC)
        return _dt.in_timezone(tz).time()

    in_tz = in_timezone
