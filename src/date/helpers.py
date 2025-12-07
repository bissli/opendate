from __future__ import annotations

import datetime as _datetime
import logging
from typing import Any

import numpy as np
import pandas as pd

from date.constants import _MAX_YEAR, _MIN_YEAR

try:
    from date._opendate import BusinessCalendar as _BusinessCalendar
    from date._opendate import IsoParser as _RustIsoParser
    from date._opendate import Parser as _RustParser
    from date._opendate import parse_time as _rust_parse_time
except ImportError:
    try:
        from _opendate import BusinessCalendar as _BusinessCalendar
        from _opendate import IsoParser as _RustIsoParser
        from _opendate import Parser as _RustParser
        from _opendate import parse_time as _rust_parse_time
    except ImportError:
        _BusinessCalendar = None
        _RustParser = None
        _RustIsoParser = None
        _rust_parse_time = None

logger = logging.getLogger(__name__)


def isdateish(x: Any) -> bool:
    return isinstance(x, (_datetime.date, _datetime.datetime, _datetime.time, pd.Timestamp, np.datetime64))


def _rust_parse_datetime(s: str, dayfirst: bool = False, yearfirst: bool = False, fuzzy: bool = True) -> _datetime.datetime | None:
    """Parse datetime string using Rust parser, return Python datetime or None.

    This is an internal helper that bridges the Rust parser to Python datetime objects.
    Returns None if parsing fails or no meaningful components are found.
    Uses current year as default when year is missing but month/day are present.
    """
    if _RustParser is None:
        return None

    try:
        parser = _RustParser(dayfirst, yearfirst)
        result = parser.parse(s, dayfirst=dayfirst, yearfirst=yearfirst, fuzzy=fuzzy)

        # Handle fuzzy_with_tokens tuple return
        if isinstance(result, tuple):
            result = result[0]

        if result is None:
            return None

        # Check if we have any meaningful date/time components
        has_date = result.year is not None or result.month is not None or result.day is not None
        has_time = result.hour is not None or result.minute is not None or result.second is not None

        if not has_date and not has_time:
            return None

        # Build datetime from components, using defaults for missing values
        now = _datetime.datetime.now()
        year = result.year if result.year is not None else now.year
        month = result.month if result.month is not None else (now.month if has_time and not has_date else 1)
        day = result.day if result.day is not None else (now.day if has_time and not has_date else 1)
        hour = result.hour if result.hour is not None else 0
        minute = result.minute if result.minute is not None else 0
        second = result.second if result.second is not None else 0
        microsecond = result.microsecond if result.microsecond is not None else 0

        # Handle timezone
        tzinfo = None
        if result.tzoffset is not None:
            tzinfo = _datetime.timezone(_datetime.timedelta(seconds=result.tzoffset))

        return _datetime.datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo)
    except Exception as e:
        logger.debug(f'Rust parser failed: {e}')
        return None


def _get_decade_bounds(year: int) -> tuple[_datetime.date, _datetime.date] | None:
    """Get decade start/end dates for caching. Returns None if outside valid range."""
    if year > _MAX_YEAR or year < _MIN_YEAR:
        return None
    decade_start = _datetime.date(year // 10 * 10, 1, 1)
    next_decade_year = (year // 10 + 1) * 10
    decade_end = _datetime.date(_MAX_YEAR, 12, 31) if next_decade_year > _MAX_YEAR else _datetime.date(next_decade_year, 1, 1)
    return decade_start, decade_end
