from __future__ import annotations

import datetime as _datetime
import logging
from typing import Any

import numpy as np
import pandas as pd

from opendate.constants import MAX_YEAR, MIN_YEAR

try:
    from opendate._opendate import BusinessCalendar as _BusinessCalendar
    from opendate._opendate import IsoParser as _RustIsoParser
    from opendate._opendate import Parser as _RustParser
    from opendate._opendate import TimeParser as _RustTimeParser
except ImportError:
    try:
        from _opendate import BusinessCalendar as _BusinessCalendar
        from _opendate import IsoParser as _RustIsoParser
        from _opendate import Parser as _RustParser
        from _opendate import TimeParser as _RustTimeParser
    except ImportError:
        _BusinessCalendar = None
        _RustParser = None
        _RustIsoParser = None
        _RustTimeParser = None

logger = logging.getLogger(__name__)

_cached_parser: _RustParser | None = None
_cached_iso_parser: _RustIsoParser | None = None
_cached_time_parser: _RustTimeParser | None = None


def _get_parser() -> _RustParser | None:
    """Get cached Parser instance.
    """
    global _cached_parser
    if _RustParser is None:
        return None
    if _cached_parser is None:
        _cached_parser = _RustParser(False, False)
    return _cached_parser


def _get_iso_parser() -> _RustIsoParser | None:
    """Get cached IsoParser instance.
    """
    global _cached_iso_parser
    if _RustIsoParser is None:
        return None
    if _cached_iso_parser is None:
        _cached_iso_parser = _RustIsoParser()
    return _cached_iso_parser


def _get_time_parser() -> _RustTimeParser | None:
    """Get cached TimeParser instance.
    """
    global _cached_time_parser
    if _RustTimeParser is None:
        return None
    if _cached_time_parser is None:
        _cached_time_parser = _RustTimeParser()
    return _cached_time_parser


def isdateish(x: Any) -> bool:
    return isinstance(x, (_datetime.date, _datetime.datetime, _datetime.time, pd.Timestamp, np.datetime64))


def _rust_parse_datetime(s: str, dayfirst: bool = False, yearfirst: bool = False, fuzzy: bool = True) -> _datetime.datetime | None:
    """Parse datetime string using Rust parser, return Python datetime or None.

    This is an internal helper that bridges the Rust parser to Python datetime objects.
    Returns None if parsing fails or no meaningful components are found.
    Uses current year as default when year is missing but month/day are present.
    """
    iso_parser = _get_iso_parser()
    if iso_parser is not None:
        try:
            result = iso_parser.isoparse(s)
            if result is not None:
                tzinfo = None
                if result.tzoffset is not None:
                    tzinfo = _datetime.timezone(_datetime.timedelta(seconds=result.tzoffset))
                return _datetime.datetime(
                    result.year, result.month, result.day,
                    result.hour or 0, result.minute or 0, result.second or 0,
                    result.microsecond or 0, tzinfo=tzinfo,
                )
        except Exception:
            pass

    parser = _get_parser()
    if parser is None:
        return None

    try:
        result = parser.parse(s, dayfirst=dayfirst, yearfirst=yearfirst, fuzzy=fuzzy)

        if isinstance(result, tuple):
            result = result[0]

        if result is None:
            return None

        has_date = result.year is not None or result.month is not None or result.day is not None
        has_time = result.hour is not None or result.minute is not None or result.second is not None

        if not has_date and not has_time:
            return None

        year = result.year
        month = result.month
        day = result.day

        if year is None or (has_time and not has_date and (month is None or day is None)):
            now = _datetime.datetime.now()
            year = year if year is not None else now.year
            month = month if month is not None else (now.month if has_time and not has_date else 1)
            day = day if day is not None else (now.day if has_time and not has_date else 1)
        else:
            month = month if month is not None else 1
            day = day if day is not None else 1

        tzinfo = None
        if result.tzoffset is not None:
            tzinfo = _datetime.timezone(_datetime.timedelta(seconds=result.tzoffset))

        return _datetime.datetime(
            year, month, day,
            result.hour or 0, result.minute or 0, result.second or 0,
            result.microsecond or 0, tzinfo=tzinfo,
        )
    except Exception as e:
        logger.debug(f'Rust parser failed: {e}')
        return None


def _rust_parse_time(s: str) -> tuple[int, int, int, int] | None:
    """Parse time string using Rust TimeParser, return (h, m, s, us) or None.

    This is an internal helper that bridges the Rust TimeParser to Python.
    Returns None if parsing fails.
    """
    time_parser = _get_time_parser()
    if time_parser is None:
        return None
    try:
        result = time_parser.parse(s)
        hour = result.hour if result.hour is not None else 0
        minute = result.minute if result.minute is not None else 0
        second = result.second if result.second is not None else 0
        microsecond = result.microsecond if result.microsecond is not None else 0
        return (hour, minute, second, microsecond)
    except Exception:
        return None


def _get_decade_bounds(year: int) -> tuple[_datetime.date, _datetime.date] | None:
    """Get decade start/end dates for caching. Returns None if outside valid range."""
    if year > MAX_YEAR or year < MIN_YEAR:
        return None
    decade_start = _datetime.date(year // 10 * 10, 1, 1)
    next_decade_year = (year // 10 + 1) * 10
    decade_end = _datetime.date(MAX_YEAR, 12, 31) if next_decade_year > MAX_YEAR else _datetime.date(next_decade_year, 1, 1)
    return decade_start, decade_end
