from __future__ import annotations

import datetime as _datetime
import functools
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


@functools.cache
def _get_parser() -> _RustParser | None:
    """Shared Parser instance, or None without the Rust extension.
    """
    return None if _RustParser is None else _RustParser(False, False)


@functools.cache
def _get_iso_parser() -> _RustIsoParser | None:
    """Shared IsoParser instance, or None without the Rust extension.
    """
    return None if _RustIsoParser is None else _RustIsoParser()


@functools.cache
def _get_time_parser() -> _RustTimeParser | None:
    """Shared TimeParser instance, or None without the Rust extension.
    """
    return None if _RustTimeParser is None else _RustTimeParser()


def isdateish(x: Any) -> bool:
    """True for a date, datetime, time, pandas Timestamp or numpy datetime64.
    """
    return isinstance(
        x,
        (
            _datetime.date,
            _datetime.datetime,
            _datetime.time,
            pd.Timestamp,
            np.datetime64,
            ))


def _rust_parse_datetime(
    s: str,
    dayfirst: bool = False,
    yearfirst: bool = False,
    fuzzy: bool = True,
) -> _datetime.datetime | None:
    """Parse datetime string using Rust parser, return Python datetime or None.

    Parameters
    ----------
    s : str
        Text to parse. An ISO 8601 string is read as ISO, whatever the
        flags below say.
    dayfirst : bool, default False
        Read an ambiguous 01/02 as day then month.
    yearfirst : bool, default False
        Read an ambiguous leading number as the year.
    fuzzy : bool, default True
        Skip words that are not part of a date or time.

    Returns
    -------
    datetime.datetime or None
        None when the extension is missing, parsing fails, or s holds no
        date or time part. A missing year is the current year, and a
        missing month or day is 1. A time with no date falls on today.
    """
    iso_parser = _get_iso_parser()
    if iso_parser is not None:
        try:
            result = iso_parser.isoparse(s)
            if result is not None:
                tzinfo = None
                if result.tzoffset is not None:
                    tzinfo = _datetime.timezone(
                        _datetime.timedelta(seconds=result.tzoffset))
                return _datetime.datetime(
                    result.year,
                    result.month,
                    result.day,
                    result.hour or 0,
                    result.minute or 0,
                    result.second or 0,
                    result.microsecond or 0,
                    tzinfo=tzinfo)
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

        has_date = (
            result.year is not None
            or result.month is not None
            or result.day is not None)
        has_time = (
            result.hour is not None
            or result.minute is not None
            or result.second is not None)

        if not has_date and not has_time:
            return None

        year = result.year
        month = result.month
        day = result.day

        if year is None:
            now = _datetime.datetime.now()
            year = now.year
            month = month if month is not None else (now.month if not has_date else 1)
            day = day if day is not None else (now.day if not has_date else 1)
        else:
            month = month if month is not None else 1
            day = day if day is not None else 1

        tzinfo = None
        if result.tzoffset is not None:
            tzinfo = _datetime.timezone(_datetime.timedelta(seconds=result.tzoffset))

        return _datetime.datetime(
            year,
            month,
            day,
            result.hour or 0,
            result.minute or 0,
            result.second or 0,
            result.microsecond or 0,
            tzinfo=tzinfo)
    except Exception as e:
        logger.debug(f'Rust parser failed: {e}')
        return None


def _rust_parse_time(s: str) -> tuple[int, int, int, int] | None:
    """Parse time string using Rust TimeParser.

    Parameters
    ----------
    s : str
        Text holding a time of day.

    Returns
    -------
    tuple[int, int, int, int] or None
        (hour, minute, second, microsecond), a missing part being 0.
        None when the extension is missing or parsing fails.
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
    """Padded decade range the calendar cache loads for year.

    Parameters
    ----------
    year : int
        Any year in the decade.

    Returns
    -------
    tuple[datetime.date, datetime.date] or None
        (start, end): the decade padded by one year each side, so 2024
        gives (2019-01-01, 2031-01-01). Clamped to Jan 1 of MIN_YEAR and
        Dec 31 of MAX_YEAR. None when year lies outside
        [MIN_YEAR, MAX_YEAR].
    """
    if year > MAX_YEAR or year < MIN_YEAR:
        return None
    start_year = max(MIN_YEAR, year // 10 * 10 - 1)
    end_year = (year // 10 + 1) * 10 + 1
    decade_start = _datetime.date(start_year, 1, 1)
    if end_year > MAX_YEAR:
        decade_end = _datetime.date(MAX_YEAR, 12, 31)
    else:
        decade_end = _datetime.date(end_year, 1, 1)
    return decade_start, decade_end
