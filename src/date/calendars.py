from __future__ import annotations

import datetime as _datetime
import zoneinfo as _zoneinfo
from abc import ABC, abstractmethod

import pandas as pd
import pandas_market_calendars as mcal

import date as _date
from date.constants import UTC, Timezone
from date.helpers import _BusinessCalendar, _get_decade_bounds


class Calendar(ABC):
    """Abstract base class for calendar definitions.

    Provides business day information including trading days,
    market hours, and holidays. Use string-based calendars for
    exchanges (via get_calendar()) or CustomCalendar for user-defined.
    """

    name: str = 'calendar'
    tz: _zoneinfo.ZoneInfo = UTC

    @abstractmethod
    def business_days(self, begdate: _datetime.date, enddate: _datetime.date) -> set:
        """Returns all business days over a range.
        """

    @abstractmethod
    def business_hours(self, begdate: _datetime.date, enddate: _datetime.date) -> dict:
        """Returns market open/close times for each business day.
        """

    @abstractmethod
    def business_holidays(self, begdate: _datetime.date, enddate: _datetime.date) -> set:
        """Returns holidays over a range.
        """

    @abstractmethod
    def _get_calendar(self, date: _datetime.date):
        """Get Rust BusinessCalendar for O(1) operations.
        """


class ExchangeCalendar(Calendar):
    """Calendar backed by pandas_market_calendars.

    Provides access to 150+ exchange calendars including NYSE, LSE,
    NASDAQ, TSX, etc. Use get_calendar('NYSE') or available_calendars()
    to discover options.
    """

    BEGDATE = _datetime.date(2000, 1, 1)
    ENDDATE = _datetime.date(2050, 1, 1)

    def __init__(self, name: str):
        self._name = name.upper()
        self._mcal = mcal.get_calendar(self._name)
        tz_str = str(self._mcal.tz)
        self._tz = Timezone(tz_str)
        self._business_days_cache: dict[tuple, set] = {}
        self._business_hours_cache: dict[tuple, dict] = {}
        self._business_holidays_cache: dict[tuple, set] = {}
        self._fast_calendar_cache: dict[tuple, object] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def tz(self) -> _zoneinfo.ZoneInfo:
        return self._tz

    def business_days(self, begdate: _datetime.date = None, enddate: _datetime.date = None) -> set:
        """Get business days for a date range (loads and caches by decade).
        """
        if begdate is None:
            begdate = self.BEGDATE
        if enddate is None:
            enddate = self.ENDDATE

        max_year = 2100
        if begdate.year > max_year:
            return set()

        decade_start = _datetime.date(begdate.year // 10 * 10, 1, 1)
        next_decade_year = (enddate.year // 10 + 1) * 10
        if next_decade_year > max_year:
            decade_end = _datetime.date(max_year, 12, 31)
        else:
            decade_end = _datetime.date(next_decade_year, 1, 1)

        return self._get_business_days_cached(decade_start, decade_end)

    def _get_business_days_cached(self, begdate: _datetime.date, enddate: _datetime.date) -> set:
        """Internal method to load and cache business days by decade.
        """
        key = (begdate, enddate)
        if key not in self._business_days_cache:
            self._business_days_cache[key] = {
                _date.Date.instance(d.date())
                for d in self._mcal.valid_days(begdate, enddate)
                }
        return self._business_days_cache[key]

    def business_hours(self, begdate: _datetime.date = None, enddate: _datetime.date = None) -> dict:
        """Get market hours for a date range.
        """
        if begdate is None:
            begdate = self.BEGDATE
        if enddate is None:
            enddate = self.ENDDATE

        key = (begdate, enddate)
        if key not in self._business_hours_cache:
            df = self._mcal.schedule(begdate, enddate, tz=self._tz)
            open_close = [
                (_date.DateTime.instance(o.to_pydatetime()),
                 _date.DateTime.instance(c.to_pydatetime()))
                for o, c in zip(df.market_open, df.market_close)
                ]
            self._business_hours_cache[key] = dict(zip(df.index.date, open_close))
        return self._business_hours_cache[key]

    def business_holidays(self, begdate: _datetime.date = None, enddate: _datetime.date = None) -> set:
        """Get business holidays for a date range.
        """
        if begdate is None:
            begdate = self.BEGDATE
        if enddate is None:
            enddate = self.ENDDATE

        key = (begdate, enddate)
        if key not in self._business_holidays_cache:
            self._business_holidays_cache[key] = {
                _date.Date.instance(d.date())
                for d in map(pd.to_datetime, self._mcal.holidays().holidays)
                if begdate <= d.date() <= enddate
                }
        return self._business_holidays_cache[key]

    def _get_fast_calendar(self, decade_start: _datetime.date, decade_end: _datetime.date):
        """Get a BusinessCalendar for O(1) business day operations.
        """
        key = (decade_start, decade_end)
        if key not in self._fast_calendar_cache:
            business_days = self._get_business_days_cached(decade_start, decade_end)
            ordinals = sorted(d.toordinal() for d in business_days)
            self._fast_calendar_cache[key] = _BusinessCalendar(ordinals)
        return self._fast_calendar_cache[key]

    def _get_calendar(self, date: _datetime.date):
        """Get the business calendar covering the decade containing the given date.
        """
        bounds = _get_decade_bounds(date.year)
        if bounds is None:
            return None
        return self._get_fast_calendar(*bounds)


class CustomCalendar(Calendar):
    """User-defined calendar with custom holidays and hours.

    Example:
        holidays = {Date(2024, 12, 26), Date(2024, 12, 27)}
        cal = CustomCalendar(
            name='MyCompany',
            holidays=holidays,
            tz=Timezone('US/Eastern'),
        )
        d = Date(2024, 12, 25).calendar(cal).b.add(days=1)
    """

    def __init__(
        self,
        name: str = 'custom',
        holidays: set[_datetime.date] | callable = None,
        tz: _zoneinfo.ZoneInfo = UTC,
        weekmask: str = 'Mon Tue Wed Thu Fri',
        open_time: _datetime.time = _datetime.time(9, 30),
        close_time: _datetime.time = _datetime.time(16, 0),
    ):
        self._name = name
        self._holidays = holidays or set()
        self._tz = tz
        self._weekmask = weekmask
        self._open_time = open_time
        self._close_time = close_time
        self._weekday_set = self._parse_weekmask(weekmask)
        self._fast_calendar_cache: dict[tuple, object] = {}

    def _parse_weekmask(self, weekmask: str) -> set[int]:
        """Parse weekmask string into set of weekday numbers (0=Mon, 6=Sun).
        """
        day_map = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6,
            }
        return {day_map[d.lower()] for d in weekmask.split() if d.lower() in day_map}

    @property
    def name(self) -> str:
        return self._name

    @property
    def tz(self) -> _zoneinfo.ZoneInfo:
        return self._tz

    def _get_holidays(self, begdate: _datetime.date, enddate: _datetime.date) -> set:
        """Get holidays for the date range.
        """
        if callable(self._holidays):
            return self._holidays(begdate, enddate)
        return {h for h in self._holidays if begdate <= h <= enddate}

    def business_days(self, begdate: _datetime.date = None, enddate: _datetime.date = None) -> set:
        """Get business days for a date range.
        """
        if begdate is None:
            begdate = _datetime.date(2000, 1, 1)
        if enddate is None:
            enddate = _datetime.date(2050, 1, 1)

        holidays = self._get_holidays(begdate, enddate)
        result = set()
        current = begdate
        while current <= enddate:
            if current.weekday() in self._weekday_set and current not in holidays:
                result.add(_date.Date.instance(current))
            current += _datetime.timedelta(days=1)
        return result

    def business_hours(self, begdate: _datetime.date = None, enddate: _datetime.date = None) -> dict:
        """Get market hours for a date range.
        """
        business_days = self.business_days(begdate, enddate)
        result = {}
        for d in business_days:
            open_dt = _date.DateTime(
                d.year, d.month, d.day,
                self._open_time.hour, self._open_time.minute, self._open_time.second,
                tzinfo=self._tz,
                )
            close_dt = _date.DateTime(
                d.year, d.month, d.day,
                self._close_time.hour, self._close_time.minute, self._close_time.second,
                tzinfo=self._tz,
                )
            result[d] = (open_dt, close_dt)
        return result

    def business_holidays(self, begdate: _datetime.date = None, enddate: _datetime.date = None) -> set:
        """Get business holidays for a date range.
        """
        if begdate is None:
            begdate = _datetime.date(2000, 1, 1)
        if enddate is None:
            enddate = _datetime.date(2050, 1, 1)
        return {_date.Date.instance(h) if not isinstance(h, _date.Date) else h
                for h in self._get_holidays(begdate, enddate)}

    def _get_calendar(self, date: _datetime.date):
        """Get the business calendar for O(1) operations.
        """
        bounds = _get_decade_bounds(date.year)
        if bounds is None:
            return None
        decade_start, decade_end = bounds
        key = (decade_start, decade_end)
        if key not in self._fast_calendar_cache:
            business_days = self.business_days(decade_start, decade_end)
            ordinals = sorted(d.toordinal() for d in business_days)
            self._fast_calendar_cache[key] = _BusinessCalendar(ordinals)
        return self._fast_calendar_cache[key]


_calendar_cache: dict[str, Calendar] = {}


def get_calendar(name: str) -> Calendar:
    """Get or create a calendar instance by name.

    Parameters
        name: Exchange name (e.g., 'NYSE', 'LSE') or registered custom name

    Returns
        Calendar instance

    Raises
        ValueError: If calendar name is not recognized
    """
    name_upper = name.upper()

    if name_upper in _calendar_cache:
        return _calendar_cache[name_upper]

    valid_names = set(mcal.get_calendar_names())
    if name_upper in valid_names or name in valid_names:
        cal = ExchangeCalendar(name)
        _calendar_cache[name_upper] = cal
        return cal

    raise ValueError(
        f'Unknown calendar: {name}. '
        f'Use available_calendars() to see valid options.'
        )


def available_calendars() -> list[str]:
    """List all available exchange calendar names.

    Returns
        Sorted list of calendar names (e.g., ['NYSE', 'LSE', 'NASDAQ', ...])
    """
    return sorted(mcal.get_calendar_names())


def register_calendar(name: str, calendar: Calendar) -> None:
    """Register a custom calendar for use by name.

    Parameters
        name: Name to register the calendar under
        calendar: Calendar instance
    """
    _calendar_cache[name.upper()] = calendar
