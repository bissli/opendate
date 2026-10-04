from __future__ import annotations

import datetime as _datetime
import zoneinfo as _zoneinfo
from abc import ABC, abstractmethod
from collections.abc import Callable

import opendate as _date
import pandas as pd
import pandas_market_calendars as mcal
from opendate.constants import MAX_YEAR, MIN_YEAR, UTC, Timezone
from opendate.helpers import _BusinessCalendar, _get_decade_bounds


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
        """Business days from begdate through enddate.

        Parameters
        ----------
        begdate : datetime.date
            First date, inclusive.
        enddate : datetime.date
            Last date, inclusive.

        Returns
        -------
        set of Date
        """

    @abstractmethod
    def business_hours(self, begdate: _datetime.date, enddate: _datetime.date) -> dict:
        """Open and close times per business day, begdate through enddate.

        Parameters
        ----------
        begdate : datetime.date
            First date, inclusive.
        enddate : datetime.date
            Last date, inclusive.

        Returns
        -------
        dict
            Maps each business day to an (open, close) pair of DateTime in
            the calendar's tz.
        """

    @abstractmethod
    def business_holidays(
        self,
        begdate: _datetime.date,
        enddate: _datetime.date) -> set:
        """Holidays from begdate through enddate.

        Parameters
        ----------
        begdate : datetime.date
            First date, inclusive.
        enddate : datetime.date
            Last date, inclusive.

        Returns
        -------
        set of Date
        """

    @abstractmethod
    def _get_calendar(self, date: _datetime.date) -> _BusinessCalendar | None:
        """Rust BusinessCalendar for O(1) business-day steps around date.

        Parameters
        ----------
        date : datetime.date
            Date the calendar must cover.

        Returns
        -------
        BusinessCalendar or None
            Built over _get_decade_bounds(date.year), or None when those
            bounds are None.
        """


class ExchangeCalendar(Calendar):
    """Calendar backed by pandas_market_calendars.

    Use get_calendar('NYSE') or available_calendars() to discover options.

    Parameters
    ----------
    name : str
        A pandas_market_calendars name, any case.

    Attributes
    ----------
    BEGDATE, ENDDATE : datetime.date
        Range a business_* method uses when begdate or enddate is None.

    Raises
    ------
    RuntimeError
        pandas_market_calendars has no calendar named name in any case.
    """

    BEGDATE = _datetime.date(2000, 1, 1)
    ENDDATE = _datetime.date(2050, 1, 1)

    def __init__(self, name: str) -> None:
        self._name = name.upper()
        mcal_name_by_upper = {n.upper(): n for n in mcal.get_calendar_names()}
        mcal_name = mcal_name_by_upper.get(self._name, self._name)
        self._mcal = mcal.get_calendar(mcal_name)
        tz_str = str(self._mcal.tz)
        self._tz = Timezone(tz_str)
        self._business_days_cache: dict[tuple, set] = {}
        self._business_hours_cache: dict[tuple, dict] = {}
        self._business_holidays_cache: dict[tuple, set] = {}
        self._fast_calendar_cache: dict[tuple, _BusinessCalendar] = {}

    @property
    def name(self) -> str:
        """Exchange name, upper case.
        """
        return self._name

    @property
    def tz(self) -> _zoneinfo.ZoneInfo:
        """Exchange time zone.
        """
        return self._tz

    def business_days(
        self,
        begdate: _datetime.date = None,
        enddate: _datetime.date = None) -> set:
        """Business days from begdate through enddate.

        Parameters
        ----------
        begdate : datetime.date, optional
            First date, inclusive. None means BEGDATE.
        enddate : datetime.date, optional
            Last date, inclusive. None means ENDDATE.

        Returns
        -------
        set of Date
            Days outside MIN_YEAR..MAX_YEAR are never included.
        """
        if begdate is None:
            begdate = self.BEGDATE
        if enddate is None:
            enddate = self.ENDDATE
        begdate = _date.Date.instance(begdate)
        enddate = _date.Date.instance(enddate)

        first_decade = max(begdate.year, MIN_YEAR) // 10
        last_decade = min(enddate.year, MAX_YEAR) // 10
        result = set()
        for decade in range(first_decade, last_decade + 1):
            bounds = _get_decade_bounds(decade * 10)
            decade_days = self._get_business_days_cached(*bounds)
            result.update(d for d in decade_days if begdate <= d <= enddate)
        return result

    def _get_business_days_cached(
        self,
        begdate: _datetime.date,
        enddate: _datetime.date) -> set:
        """Internal method to load and cache business days by decade.
        """
        key = (begdate, enddate)
        if key not in self._business_days_cache:
            self._business_days_cache[key] = {
                _date.Date.instance(d.date())
                for d in self._mcal.valid_days(begdate, enddate)
                }
        return self._business_days_cache[key]

    def business_hours(
        self,
        begdate: _datetime.date = None,
        enddate: _datetime.date = None) -> dict:
        """Market open and close per session, begdate through enddate.

        Parameters
        ----------
        begdate : datetime.date, optional
            First date, inclusive. None means BEGDATE.
        enddate : datetime.date, optional
            Last date, inclusive. None means ENDDATE.

        Returns
        -------
        dict
            Maps a datetime.date to an (open, close) pair of DateTime in the
            exchange zone.
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
        return dict(self._business_hours_cache[key])

    def business_holidays(
        self,
        begdate: _datetime.date = None,
        enddate: _datetime.date = None) -> set:
        """Exchange holidays from begdate through enddate.

        Parameters
        ----------
        begdate : datetime.date, optional
            First date, inclusive. None means BEGDATE.
        enddate : datetime.date, optional
            Last date, inclusive. None means ENDDATE.

        Returns
        -------
        set of Date
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
        return set(self._business_holidays_cache[key])

    def _get_fast_calendar(
        self,
        decade_start: _datetime.date,
        decade_end: _datetime.date) -> _BusinessCalendar:
        """Get a BusinessCalendar for O(1) business day operations.
        """
        key = (decade_start, decade_end)
        if key not in self._fast_calendar_cache:
            business_days = self._get_business_days_cached(decade_start, decade_end)
            ordinals = sorted(d.toordinal() for d in business_days)
            self._fast_calendar_cache[key] = _BusinessCalendar(ordinals)
        return self._fast_calendar_cache[key]

    def _get_calendar(self, date: _datetime.date) -> _BusinessCalendar | None:
        """Cached BusinessCalendar for the padded decade around date, or None.
        """
        bounds = _get_decade_bounds(date.year)
        if bounds is None:
            return None
        return self._get_fast_calendar(*bounds)


class CustomCalendar(Calendar):
    """User-defined calendar with custom holidays and hours.

    Parameters
    ----------
    name : str, default 'custom'
        Value of the name property. register_calendar sets the lookup key.
    holidays : set of datetime.date or callable, optional
        Closed dates. A callable takes (begdate, enddate) and returns the
        holidays in that range. None means no holidays.
    tz : ZoneInfo, default UTC
        Zone of the business_hours open and close times.
    weekmask : str, default 'Mon Tue Wed Thu Fri'
        Open weekdays as three-letter names, any case. Any other token, such
        as 'Monday', is dropped without error.
    open_time : datetime.time, default 09:30
        Daily open, wall clock in tz.
    close_time : datetime.time, default 16:00
        Daily close, wall clock in tz.

    Examples
    --------
    >>> holidays = {Date(2024, 12, 26), Date(2024, 12, 27)}
    >>> cal = CustomCalendar(
    ...     name='MyCompany',
    ...     holidays=holidays,
    ...     tz=Timezone('US/Eastern'))
    >>> Date(2024, 12, 25).calendar(cal).b.add(days=1)
    Date(2024, 12, 30)
    """

    def __init__(
        self,
        name: str = 'custom',
        holidays: set[_datetime.date] | Callable | None = None,
        tz: _zoneinfo.ZoneInfo = UTC,
        weekmask: str = 'Mon Tue Wed Thu Fri',
        open_time: _datetime.time = _datetime.time(9, 30),
        close_time: _datetime.time = _datetime.time(16, 0),
    ) -> None:
        self._name = name
        self._holidays = holidays or set()
        self._tz = tz
        self._weekmask = weekmask
        self._open_time = open_time
        self._close_time = close_time
        self._weekday_set = self._parse_weekmask(weekmask)
        self._fast_calendar_cache: dict[tuple, _BusinessCalendar] = {}

    def _parse_weekmask(self, weekmask: str) -> set[int]:
        """Parse weekmask string into set of weekday numbers (0=Mon, 6=Sun).
        """
        day_map = {
            'mon': 0,
            'tue': 1,
            'wed': 2,
            'thu': 3,
            'fri': 4,
            'sat': 5,
            'sun': 6,
            }
        return {day_map[d.lower()] for d in weekmask.split() if d.lower() in day_map}

    @property
    def name(self) -> str:
        """Name given at construction.
        """
        return self._name

    @property
    def tz(self) -> _zoneinfo.ZoneInfo:
        """Zone of the business_hours open and close times.
        """
        return self._tz

    def _get_holidays(self, begdate: _datetime.date, enddate: _datetime.date) -> set:
        """Holidays from begdate through enddate; a callable's result as is.
        """
        if callable(self._holidays):
            return self._holidays(begdate, enddate)
        return {h for h in self._holidays if begdate <= h <= enddate}

    def business_days(
        self,
        begdate: _datetime.date = None,
        enddate: _datetime.date = None) -> set:
        """Weekmask days from begdate through enddate, less holidays.

        Parameters
        ----------
        begdate : datetime.date, optional
            First date, inclusive. None means 2000-01-01.
        enddate : datetime.date, optional
            Last date, inclusive. None means 2050-01-01.

        Returns
        -------
        set of Date
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

    def business_hours(
        self,
        begdate: _datetime.date = None,
        enddate: _datetime.date = None) -> dict:
        """Open and close times per business day, begdate through enddate.

        Parameters
        ----------
        begdate : datetime.date, optional
            First date, inclusive. None means 2000-01-01.
        enddate : datetime.date, optional
            Last date, inclusive. None means 2050-01-01.

        Returns
        -------
        dict
            Maps each business day, a Date, to an (open, close) pair of
            DateTime at open_time and close_time in tz.
        """
        business_days = self.business_days(begdate, enddate)
        result = {}
        for d in business_days:
            open_dt = _date.DateTime(
                d.year,
                d.month,
                d.day,
                self._open_time.hour,
                self._open_time.minute,
                self._open_time.second,
                tzinfo=self._tz)
            close_dt = _date.DateTime(
                d.year,
                d.month,
                d.day,
                self._close_time.hour,
                self._close_time.minute,
                self._close_time.second,
                tzinfo=self._tz)
            result[d] = (open_dt, close_dt)
        return result

    def business_holidays(
        self,
        begdate: _datetime.date = None,
        enddate: _datetime.date = None) -> set:
        """Holidays from begdate through enddate.

        Parameters
        ----------
        begdate : datetime.date, optional
            First date, inclusive. None means 2000-01-01.
        enddate : datetime.date, optional
            Last date, inclusive. None means 2050-01-01.

        Returns
        -------
        set of Date
            A callable holidays source's result is returned unfiltered.
        """
        if begdate is None:
            begdate = _datetime.date(2000, 1, 1)
        if enddate is None:
            enddate = _datetime.date(2050, 1, 1)
        return {_date.Date.instance(h) if not isinstance(h, _date.Date) else h
                for h in self._get_holidays(begdate, enddate)}

    def _get_calendar(self, date: _datetime.date) -> _BusinessCalendar | None:
        """Cached BusinessCalendar for the padded decade around date, or None.
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
_default_calendar: str = 'NYSE'


def get_default_calendar() -> str:
    """Upper-case name of the calendar used when none is given, initially NYSE.
    """
    return _default_calendar


def set_default_calendar(name: str) -> None:
    """Set the calendar used when none is given.

    Parameters
    ----------
    name : str
        Exchange name such as 'NYSE' or 'LSE', or a name passed to
        register_calendar. Any case.

    Raises
    ------
    ValueError
        name is neither an exchange nor a registered calendar.
    """
    global _default_calendar
    get_calendar(name)
    _default_calendar = name.upper()


def get_calendar(name: str) -> Calendar:
    """Calendar registered under name, or an exchange calendar built once.

    Parameters
    ----------
    name : str
        Name passed to register_calendar, or an exchange name such as 'NYSE'
        or 'LSE'. Any case.

    Returns
    -------
    Calendar
        The same instance on every call for one name.

    Raises
    ------
    ValueError
        name is neither an exchange nor a registered calendar.
    """
    name_upper = name.upper()

    if name_upper in _calendar_cache:
        return _calendar_cache[name_upper]

    valid_names = {n.upper() for n in mcal.get_calendar_names()}
    if name_upper in valid_names:
        cal = ExchangeCalendar(name)
        _calendar_cache[name_upper] = cal
        return cal

    raise ValueError(
        f'Unknown calendar: {name}. '
        f'Use available_calendars() to see valid options.')


def available_calendars() -> list[str]:
    """Sorted pandas_market_calendars names; excludes register_calendar names.
    """
    return sorted(mcal.get_calendar_names())


def register_calendar(name: str, calendar: Calendar) -> None:
    """Make calendar available to get_calendar and Date.calendar by name.

    Parameters
    ----------
    name : str
        Lookup key, any case. It shadows an exchange of the same name.
    calendar : Calendar
        Instance returned for name; its own name property is left as is.
    """
    _calendar_cache[name.upper()] = calendar
